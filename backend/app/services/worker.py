#!/usr/bin/env python3
"""
Dark Web Scraper Worker - Fixed & Production Ready
"""

import asyncio
import logging
import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

from playwright.async_api import async_playwright
from sqlalchemy import select

from app.services.kafka_consumer import KafkaConsumer, KafkaProducerConsumer
from app.services.es_client import ESClient
from app.services.scraper_utils import (
    extract_entities,
    find_keyword_context,
    calculate_enhanced_risk_score,
    analyze_content_sentiment,
    sanitize_filename,
    sha1_short,
    random_delay,
    validate_onion_url,
    search_ahmia,
)
from app.services.tor_manager import TorManager
from app.services.deduplication import DeduplicationService
from app.services.alert_sender import AlertSender
from app.services.crypto_utils import decrypt_credential  # Added decryption import
from app.database.database import AsyncSessionLocal
from app.models.alert import Alert
from app.models.monitoring_result import MonitoringResult

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOR_SOCKS = os.getenv("TOR_SOCKS", "127.0.0.1:9050")
OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE", "./dark_web_results"))
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
RISK_LEVEL_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _get_user_uuid(user_id_str: str) -> uuid.UUID:
    """Convert user_id string to UUID, handling both UUID and string formats"""
    try:
        if isinstance(user_id_str, uuid.UUID):
            return user_id_str
        # Try parsing as UUID
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError, TypeError):
        # Fallback for string identifiers
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id_str))


class DarkWebWorker:
    def __init__(self):
        self.es_client = ESClient(ES_URL)
        self.tor_manager = TorManager(TOR_SOCKS)
        self.consumer = KafkaConsumer(
            topics=["ad_hoc_jobs", "monitor_jobs"],
            bootstrap_servers=KAFKA_BOOTSTRAP
        )
        self.status_producer = KafkaProducerConsumer(KAFKA_BOOTSTRAP)
        self.alert_sender = AlertSender()
        self.output_base = OUTPUT_BASE
        self.output_base.mkdir(parents=True, exist_ok=True)
        # Limit concurrent investigations to prevent overwhelming the system (CPU/Memory)
        max_concurrent = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"[*] DarkWebWorker initialized with max_concurrent_jobs={max_concurrent}")
    
    async def check_duplicate_and_get_alert_triggers(
        self,
        url: str,
        content: str,
        user_id: str
    ) -> tuple:
        """
        Check if content is duplicate and get matching alerts
        Returns: (is_duplicate, duplicate_of_id, matching_alerts)
        """
        try:
            content_hash = DeduplicationService.generate_content_hash(content, url)
            user_uuid = _get_user_uuid(user_id)
            
            async with AsyncSessionLocal() as db:
                # Check for exact hash match (duplicate)
                result = await db.execute(
                    select(MonitoringResult).where(
                        MonitoringResult.content_hash == content_hash,
                        MonitoringResult.user_id == user_uuid,
                        MonitoringResult.target_url == url
                    ).order_by(MonitoringResult.created_at.desc())
                )
                existing = result.scalars().first()
                
                is_duplicate = existing is not None
                duplicate_of_id = existing.id if existing else None
                
                # Get active alerts for user
                alert_result = await db.execute(
                    select(Alert).where(
                        Alert.user_id == user_uuid,
                        Alert.is_active == True
                    )
                )
                alerts = alert_result.scalars().all()
                
                return is_duplicate, duplicate_of_id, alerts
        
        except Exception as e:
            logger.error(f"[!] Error checking duplicates: {e}")
            return False, None, []
    
    async def trigger_alerts_for_finding(
        self,
        finding: dict,
        alerts: list,
        user_id: str
    ) -> dict:
        """
        Check all active alerts and trigger if conditions met
        Returns alert triggering details
        """
        risk_level = finding.get("risk_level", "low")
        risk_score = finding.get("risk_score", 0)
        text_content = (finding.get("text_excerpt") or "") + " " + (finding.get("title") or "")
        url = finding.get("url", "")
        
        triggered_alerts = []
        
        for alert in alerts:
            keyword = alert.keyword.lower()
            risk_threshold = alert.risk_level_threshold
            
            # Check if keyword is found in content
            if keyword in text_content.lower():
                # Check if risk level meets threshold
                threshold_level = RISK_LEVEL_ORDER.get(risk_threshold, 2)
                current_level = RISK_LEVEL_ORDER.get(risk_level, 1)
                
                if current_level >= threshold_level:
                    logger.info(f"[Alert] Keyword '{keyword}' found in {url} with risk {risk_level}")
                    triggered_alerts.append({
                        "id": str(alert.id),
                        "keyword": keyword,
                        "risk_level_threshold": risk_threshold,
                        "notification_type": alert.notification_type,
                        "notification_endpoint": alert.notification_endpoint
                    })
        
        # Send alerts asynchronously
        triggered_alert_ids = []
        if triggered_alerts:
            triggered_alert_ids = await self.alert_sender.send_alerts(
                triggered_alerts,
                finding
            )
            logger.info(f"[Alert] Triggered {len(triggered_alert_ids)} alerts for {url}")
        
        return {
            "alerts_triggered": triggered_alert_ids,
            "alert_count": len(triggered_alert_ids)
        }
    
    async def save_monitoring_result(
        self,
        finding: dict,
        is_duplicate: bool,
        duplicate_of_id: str,
        alerts_triggered: list,
        user_id: str,
        job_id: str,
        monitor_job_id: str = None
    ) -> MonitoringResult:
        """Save monitoring result to database"""
        try:
            content_hash = DeduplicationService.generate_content_hash(
                finding.get("text_excerpt", ""),
                finding.get("url", "")
            )
            user_uuid = _get_user_uuid(user_id)
            
            job_uuid = uuid.UUID(job_id) if job_id and not isinstance(job_id, uuid.UUID) else job_id
            monitor_job_uuid = uuid.UUID(monitor_job_id) if monitor_job_id and not isinstance(monitor_job_id, uuid.UUID) else None
            duplicate_of_uuid = uuid.UUID(duplicate_of_id) if duplicate_of_id and not isinstance(duplicate_of_id, uuid.UUID) else None
            
            async with AsyncSessionLocal() as db:
                result = MonitoringResult(
                    job_id=job_uuid,
                    user_id=user_uuid,
                    target_url=finding.get("url"),
                    title=finding.get("title"),
                    text_excerpt=finding.get("text_excerpt"),
                    risk_level=finding.get("risk_level"),
                    risk_score=finding.get("risk_score", 0),
                    threat_indicators=finding.get("threat_indicators", []),
                    content_hash=content_hash,
                    is_duplicate=is_duplicate,
                    duplicate_of_id=duplicate_of_uuid,
                    monitor_job_id=monitor_job_uuid,
                    alerts_triggered=alerts_triggered,
                    detected_at=datetime.now(timezone.utc)
                )
                
                db.add(result)
                await db.commit()
                logger.info(f"[Result] Saved monitoring result {result.id}")
                return result
        
        except Exception as e:
            logger.error(f"[!] Failed to save monitoring result: {e}")
            return None
    
    async def process_message(self, topic: str, message: dict):
        """Route message to appropriate handler with concurrency control"""
        try:
            job_id = message.get("job_id")
            job_type = message.get("job_type")
            
            logger.info(f"[→] Queuing {job_type} job: {job_id} (Waiting for semaphore slot...)")
            
            async with self.semaphore:
                logger.info(f"[→] Processing {job_type} job: {job_id}")
                
                if job_type == "ad_hoc":
                    await self.handle_ad_hoc(job_id, message)
                elif job_type == "monitor":
                    await self.handle_monitor(job_id, message)
                else:
                    logger.warning(f"Unknown job type: {job_type}")
        
        except Exception as e:
            logger.error(f"[!] Message processing error: {e}")

    async def handle_ad_hoc(self, job_id: str, payload: dict):
        """Handle ad-hoc search job"""
        keyword = payload.get("keyword").strip() if payload.get("keyword") else None
        max_results = payload.get("max_results")
        user_id = payload.get("user_id")

        if not keyword:
            await self.status_producer.send_status(job_id, "FAILED", {"error": "No keyword provided"})
            return

        try:
            discovery_max = max_results + 100 if max_results else 900
            logger.info(f"[*] Starting ad-hoc discovery for keyword: '{keyword}' (unlimited scrape mode)" if not max_results else f"[*] Starting ad-hoc discovery for keyword: '{keyword}' (max: {max_results})")

            # === FIXED: Run discovery and load results from disk ===
            try:
                output_dir = await search_ahmia(
                    keyword=keyword,
                    max_results=discovery_max,
                    rotate_identity=True,
                    deep_analyze=False
                )
                logger.info(f"[*] Discovery phase completed → results in {output_dir}")
            except Exception as e:
                raise RuntimeError(f"Discovery engine failed: {e}")

            raw_json_path = output_dir / "0_discovered_raw.json"
            if not raw_json_path.exists():
                raise FileNotFoundError(f"Discovery JSON not found: {raw_json_path}")

            with open(raw_json_path, "r", encoding="utf-8") as f:
                discovered = json.load(f)

            valid_links = {
                item["url"]: item for item in discovered
                if item.get("category") != "blocked_illegal"
            }.values()

            onion_links = [item["url"] for item in valid_links]
            logger.info(f"[*] Found {len(onion_links)} valid .onion links to scrape")

            if not onion_links:
                await self.status_producer.send_status(job_id, "COMPLETED", {
                    "findings_count": 0,
                    "reason": "No valid links after filtering"
                })
                return

            session_dir = self.output_base / f"{sanitize_filename(keyword)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{job_id[:8]}"
            session_dir.mkdir(parents=True, exist_ok=True)

            findings = []
            links_to_scrape = onion_links if not max_results else onion_links[:max_results]
            total_links = len(links_to_scrape)
            
            await self.status_producer.send_status(job_id, "PROCESSING", {
                "sites_scraped": 0,
                "total_sites": total_links,
                "progress": 0
            })
            
            async with async_playwright() as pw:
                for idx, link in enumerate(links_to_scrape, 1):
                    try:
                        await random_delay(2, 6)

                        logger.info(f"[+] Scraping ({idx}/{total_links}): {link}")

                        if not validate_onion_url(link):
                            logger.warning(f"[!] Invalid .onion URL, skipping: {link}")
                            continue

                        meta = await self.scrape_onion_page(pw, link, session_dir, keyword)

                        if meta.get("ok"):
                            risk_level, risk_score, threat_indicators = calculate_enhanced_risk_score(meta, keyword)
                            sentiment = await analyze_content_sentiment(
                                (meta.get("title") or "") + " " + (meta.get("text_excerpt") or "")
                            )

                            finding = {
                                "id": str(uuid.uuid4()),
                                "url": link,
                                "title": meta.get("title"),
                                "text_excerpt": meta.get("text_excerpt"),
                                "description": meta.get("meta_description"),
                                "risk_level": risk_level,
                                "risk_score": risk_score,
                                "threat_indicators": threat_indicators,
                                "relevance_score": meta.get("relevance_score", 0),
                                "sentiment": sentiment.get("sentiment"),
                                "threat_sentiment": sentiment.get("threat_sentiment"),
                                "entities": meta.get("entities", {}),
                                "keywords_found": meta.get("keywords_found", []),
                                "language": meta.get("language"),
                                "screenshot_file": meta.get("screenshot_file"),
                                "text_file": meta.get("text_file"),
                                "html_file": meta.get("raw_html_file"),
                                "scraped_at": datetime.now(timezone.utc).isoformat(),
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "job_id": job_id,
                                "user_id": user_id,
                                "keyword": keyword
                            }

                            await self.es_client.index_finding(finding)
                            findings.append(finding)
                            logger.info(f"[Success] Indexed: {link} | Risk: {risk_level} | Score: {risk_score:.1f}")

                        progress = int((idx / total_links) * 100)
                        await self.status_producer.send_status(job_id, "PROCESSING", {
                            "sites_scraped": idx,
                            "total_sites": total_links,
                            "findings_count": len(findings),
                            "progress": progress
                        })

                        await random_delay(1, 4)

                    except Exception as e:
                        logger.error(f"[!] Failed to scrape {link}: {e}")
                        continue

            logger.info(f"[Success] Ad-hoc job {job_id} completed → {len(findings)} findings indexed")
            await self.status_producer.send_status(job_id, "COMPLETED", {
                "findings_count": len(findings),
                "discovered_count": len(onion_links),
                "session_dir": str(session_dir),
                "sites_scraped": total_links,
                "total_sites": total_links,
                "progress": 100
            })

        except Exception as e:
            logger.error(f"[Failed] Ad-hoc job {job_id} failed: {e}")
            await self.status_producer.send_status(job_id, "FAILED", {"error": str(e)})

    async def handle_monitor(self, job_id: str, payload: dict):
        """Handle monitoring job with optional authentication"""
        url = payload.get("target_url") or payload.get("url")
        user_id = payload.get("user_id")
        monitor_job_id = payload.get("monitor_job_id")
        
        auth_config = {
            "auth_username": payload.get("auth_username"),
            "auth_password": payload.get("auth_password"),
            "login_path": payload.get("login_path"),
            "username_selector": payload.get("username_selector"),
            "password_selector": payload.get("password_selector"),
            "submit_selector": payload.get("submit_selector")
        }
        has_auth = bool(auth_config.get("auth_username") and auth_config.get("auth_password"))
        
        if not url:
            await self.status_producer.send_status(job_id, "FAILED", {"error": "No URL provided"})
            return

        try:
            logger.info(f"[Monitor] Starting scrape for: {url} (auth: {has_auth})")

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    proxy={"server": f"socks5://{TOR_SOCKS}"},
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(viewport={"width": 1280, "height": 900})
                page = await context.new_page()

                if has_auth:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    auth_success = await self.perform_authentication(page, auth_config)
                    
                    if not auth_success:
                        await self.status_producer.send_status(job_id, "FAILED", {
                            "error": "Authentication failed",
                            "url": url
                        })
                        await browser.close()
                        return
                    
                    # After successful auth, navigate to target URL
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                else:
                    # No auth required, navigate directly
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Proceed with normal scraping
                meta = await self.scrape_onion_page(pw, url, self.output_base, "")

                if meta.get("ok"):
                    risk_level, risk_score, threat_indicators = calculate_enhanced_risk_score(meta)
                    sentiment = await analyze_content_sentiment(
                        (meta.get("title") or "") + " " + (meta.get("text_excerpt") or "")
                    )

                    finding = {
                        "id": str(uuid.uuid4()),
                        "url": url,
                        "title": meta.get("title"),
                        "text_excerpt": meta.get("text_excerpt"),
                        "risk_level": risk_level,
                        "risk_score": risk_score,
                        "threat_indicators": threat_indicators,
                        "sentiment": sentiment.get("sentiment"),
                        "threat_sentiment": sentiment.get("threat_sentiment"),
                        "entities": meta.get("entities", {}),
                        "keywords_found": meta.get("keywords_found", []),
                        "screenshot_file": meta.get("screenshot_file"),
                        "text_file": meta.get("text_file"),
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                        "job_id": job_id,
                        "user_id": user_id,
                        "monitor_job": True
                    }
                    
                    is_duplicate, duplicate_of_id, active_alerts = await self.check_duplicate_and_get_alert_triggers(
                        url, meta.get("text_excerpt", ""), user_id
                    )
                    
                    alert_results = await self.trigger_alerts_for_finding(
                        finding, [{"id": str(a.id), "keyword": a.keyword, "risk_level_threshold": a.risk_level_threshold, "notification_type": a.notification_type, "notification_endpoint": a.notification_endpoint} for a in active_alerts], user_id
                    )
                    
                    await self.save_monitoring_result(
                        finding,
                        is_duplicate,
                        duplicate_of_id,
                        alert_results.get("alerts_triggered", []),
                        user_id,
                        job_id,
                        monitor_job_id
                    )

                    await self.es_client.index_finding(finding)
                    logger.info(f"[Monitor] Successfully scraped {url}")
                else:
                    await self.status_producer.send_status(job_id, "FAILED", {"error": meta.get("error")})
                
                await browser.close()

        except Exception as e:
            logger.error(f"[Monitor] Failed: {e}")
            await self.status_producer.send_status(job_id, "FAILED", {"error": str(e)})
    
    async def scrape_onion_page(self, playwright, url: str, out_dir: Path, keyword: str = ""):
        """Scrape .onion URL and return metadata — Now captures FULL page text with no limits"""
        browser = await playwright.chromium.launch(
            headless=True,
            proxy={"server": f"socks5://{TOR_SOCKS}"},
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        
        safe_name = sanitize_filename(url) + "_" + sha1_short(url)
        site_dir = out_dir / safe_name
        site_dir.mkdir(parents=True, exist_ok=True)
        
        meta = {
            "url": url,
            "safe_name": safe_name,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
            "error": None,
            "title": "",
            "text_excerpt": "",
            "keywords_found": [],
            "entities": {},
            "screenshot_file": None,
            "text_file": None,
            "raw_html_file": None,
            "relevance_score": 0.0
        }
        
        try:
            logger.info(f"[+] Opening {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)  # Slightly longer wait for dynamic content
            
            # Get page content
            raw_html = await page.content()
            
            # Extract FULL visible text using JavaScript (clean, complete, no hidden elements)
            visible_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            visible_text = visible_text or ""
            
            # Save full HTML
            if raw_html.strip():
                html_path = site_dir / f"{safe_name}.html"
                html_path.write_text(raw_html, encoding="utf-8", errors="replace")
                meta["raw_html_file"] = str(html_path)
            
            # Take screenshot
            try:
                shot_path = site_dir / f"{safe_name}.png"
                await page.screenshot(path=str(shot_path), full_page=True)
                meta["screenshot_file"] = str(shot_path)
            except Exception as e:
                logger.warning(f"Screenshot failed: {e}")
            
            # Save FULL visible text to .txt file
            if visible_text.strip():
                text_path = site_dir / f"{safe_name}.txt"
                text_path.write_text(visible_text, encoding="utf-8", errors="replace")
                meta["text_file"] = str(text_path)
            
            # === CRITICAL CHANGE: Use FULL text everywhere ===
            # No truncation — text_excerpt now holds the complete visible text
            meta["text_excerpt"] = visible_text
            
            # Extract title
            try:
                title_elem = await page.query_selector("title")
                if title_elem:
                    meta["title"] = await title_elem.inner_text()
            except:
                pass
            
            meta["title"] = meta["title"] or "Untitled"
            
            # Extract entities from combined raw HTML + visible text (max coverage)
            full_text = raw_html + "\n" + visible_text if raw_html and visible_text else visible_text
            meta["entities"] = extract_entities(full_text)
            
            # Find keyword context and relevance using FULL visible text
            if keyword and visible_text:
                contexts = find_keyword_context(visible_text, keyword)
                meta["keywords_found"] = contexts
                
                # Relevance based on keyword frequency in full text
                freq = len([m for m in re.finditer(re.escape(keyword), visible_text, flags=re.I)])
                # Avoid division by zero; use character count for density
                text_length = len(visible_text)
                meta["relevance_score"] = round((freq / max(1, text_length)) * 10000, 4) if text_length > 0 else 0.0
            
            meta["ok"] = True
            logger.info(f"[Success] Scraped {url} | Full text length: {len(visible_text)} characters")
        
        except Exception as e:
            meta["error"] = str(e)
            logger.error(f"[!] Scrape error for {url}: {e}")
        
        finally:
            await context.close()
            await browser.close()
            return meta
    
    async def perform_authentication(self, page, auth_config: dict) -> bool:
        """
        Perform authentication on a dark web site
        Returns True if successful, False otherwise
        """
        try:
            username_raw = auth_config.get("auth_username")
            password_raw = auth_config.get("auth_password")
            
            # Try to decrypt, but fall back to plaintext if decryption fails
            try:
                username = decrypt_credential(username_raw) if username_raw else None
                password = decrypt_credential(password_raw) if password_raw else None
            except Exception as e:
                logger.warning(f"[Auth] Using plaintext credentials (decryption not available): {e}")
                username = username_raw
                password = password_raw
            
            if not username or not password:
                logger.warning("[Auth] Missing credentials after decryption")
                return False
            
            login_path = auth_config.get("login_path", "")
            username_selector = auth_config.get("username_selector", 'input[name="username"]')
            password_selector = auth_config.get("password_selector", 'input[name="password"]')
            submit_selector = auth_config.get("submit_selector", 'button[type="submit"]')
            
            current_url = page.url
            login_url = current_url.rstrip('/') + login_path if login_path else current_url
            
            logger.info(f"[Auth] Attempting login at: {login_url}")
            
            # Navigate to login page if different
            if login_path:
                await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
            
            # Fill username field
            await page.wait_for_selector(username_selector, timeout=10000)
            await page.fill(username_selector, username)
            logger.info(f"[Auth] Filled username field")
            
            # Fill password field
            await page.fill(password_selector, password)
            logger.info(f"[Auth] Filled password field")
            
            # Submit form
            await page.click(submit_selector)
            logger.info(f"[Auth] Clicked submit button")
            
            # Wait for navigation
            await page.wait_for_load_state("networkidle", timeout=60000)
            
            # Check if login was successful
            # Look for common error indicators
            page_content = await page.content()
            error_indicators = [
                "login failed", "invalid credentials", "incorrect password",
                "authentication failed", "wrong username", "access denied"
            ]
            
            if any(indicator in page_content.lower() for indicator in error_indicators):
                logger.error("[Auth] Login failed - error message detected")
                return False
            
            # Check if we're still on login page
            if "login" in page.url.lower() and login_path:
                logger.error("[Auth] Still on login page after submission")
                return False
            
            logger.info("[Auth] Login successful")
            return True
            
        except Exception as e:
            logger.error(f"[Auth] Authentication failed: {e}")
            return False
    
    async def run(self):
        try:
            await self.consumer.connect()
            await self.status_producer.connect()
            logger.info("[Success] DarkWebWorker started — waiting for jobs...")
            await self.consumer.consume(self.process_message)
        except Exception as e:
            logger.error(f"[Failed] Worker error: {e}")
            sys.exit(1)
        finally:
            await self.consumer.close()
            await self.status_producer.close()


async def main():
    worker = DarkWebWorker()
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[!] Worker interrupted by user")
