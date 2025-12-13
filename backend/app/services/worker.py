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
from datetime import datetime
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
            
            async with AsyncSessionLocal() as db:
                result = MonitoringResult(
                    job_id=job_id,
                    user_id=user_uuid,
                    target_url=finding.get("url"),
                    title=finding.get("title"),
                    text_excerpt=finding.get("text_excerpt"),
                    risk_level=finding.get("risk_level"),
                    risk_score=finding.get("risk_score", 0),
                    threat_indicators=finding.get("threat_indicators", []),
                    content_hash=content_hash,
                    is_duplicate=is_duplicate,
                    duplicate_of_id=duplicate_of_id,
                    monitor_job_id=monitor_job_id,
                    alerts_triggered=alerts_triggered,
                    detected_at=datetime.utcnow()
                )
                
                db.add(result)
                await db.commit()
                logger.info(f"[Result] Saved monitoring result {result.id}")
                return result
        
        except Exception as e:
            logger.error(f"[!] Failed to save monitoring result: {e}")
            return None
    
    async def process_message(self, topic: str, message: dict):
        """Route message to appropriate handler"""
        try:
            job_id = message.get("job_id")
            job_type = message.get("job_type")
            
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
        keyword = payload.get("keyword")
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
                                "scraped_at": datetime.utcnow().isoformat(),
                                "created_at": datetime.utcnow().isoformat(),
                                "job_id": job_id,
                                "user_id": user_id,
                                "keyword": keyword
                            }

                            await self.es_client.index_finding(finding)
                            findings.append(finding)
                            logger.info(f"[Success] Indexed: {link} | Risk: {risk_level} | Score: {risk_score:.1f}")

                        await random_delay(1, 4)

                    except Exception as e:
                        logger.error(f"[!] Failed to scrape {link}: {e}")
                        continue

            logger.info(f"[Success] Ad-hoc job {job_id} completed → {len(findings)} findings indexed")
            await self.status_producer.send_status(job_id, "COMPLETED", {
                "findings_count": len(findings),
                "discovered_count": len(onion_links),
                "session_dir": str(session_dir)
            })

        except Exception as e:
            logger.error(f"[Failed] Ad-hoc job {job_id} failed: {e}")
            await self.status_producer.send_status(job_id, "FAILED", {"error": str(e)})

    async def handle_monitor(self, job_id: str, payload: dict):
        """Enhanced monitor handler with dedup and alert triggering"""
        url = payload.get("target_url") or payload.get("url")
        user_id = payload.get("user_id")
        monitor_job_id = payload.get("monitor_job_id")

        if not url:
            await self.status_producer.send_status(job_id, "FAILED", {"error": "No URL provided"})
            return

        try:
            logger.info(f"[Monitor] Starting monitor scrape for: {url}")

            async with async_playwright() as pw:
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
                        "scraped_at": datetime.utcnow().isoformat(),
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
                    logger.info(f"[Success] Monitor job {job_id} completed | Risk: {risk_level} | Alerts: {alert_results.get('alert_count', 0)}")

                    await self.status_producer.send_status(job_id, "COMPLETED", {
                        "findings_count": 1,
                        "risk_level": risk_level,
                        "is_duplicate": is_duplicate,
                        "alerts_triggered": len(alert_results.get("alerts_triggered", []))
                    })
                else:
                    await self.status_producer.send_status(job_id, "FAILED", {"error": meta.get("error")})

        except Exception as e:
            logger.error(f"[Failed] Monitor job failed: {e}")
            await self.status_producer.send_status(job_id, "FAILED", {"error": str(e)})

    async def scrape_onion_page(self, playwright, url: str, out_dir: Path, keyword: str = ""):
        """Scrape .onion URL and return metadata — FIXED to handle None/empty safely"""
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
            "scraped_at": datetime.utcnow().isoformat(),
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
            await asyncio.sleep(1)
            
            # Get page content
            raw_html = await page.content()
            visible_text = await page.inner_text("body") if await page.query_selector("body") else ""
            
            # Ensure visible_text is always a string
            visible_text = visible_text or ""
            
            # Save HTML
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
            
            # Save text + excerpt
            if visible_text.strip():
                text_path = site_dir / f"{safe_name}.txt"
                text_path.write_text(visible_text, encoding="utf-8", errors="replace")
                meta["text_file"] = str(text_path)
            
            meta["text_excerpt"] = visible_text[:1000]  # Longer for better analysis
            
            # Extract title
            try:
                title_elem = await page.query_selector("title")
                if title_elem:
                    meta["title"] = await title_elem.inner_text()
            except:
                pass
            
            meta["title"] = meta["title"] or "Untitled"  # Default to string
            
            # Extract entities
            full_text = raw_html + "\n" + visible_text if raw_html and visible_text else visible_text
            meta["entities"] = extract_entities(full_text)
            
            # Find keyword context
            if keyword and visible_text:
                contexts = find_keyword_context(visible_text, keyword)
                meta["keywords_found"] = contexts
                freq = len([m for m in re.finditer(re.escape(keyword), visible_text, flags=re.I)])
                meta["relevance_score"] = round((freq / max(1, len(visible_text))) * 10000, 4)
            
            meta["ok"] = True
            logger.info(f"[Success] Scraped {url}")
        
        except Exception as e:
            meta["error"] = str(e)
            logger.error(f"[!] Scrape error for {url}: {e}")
        
        finally:
            await context.close()
            await browser.close()
            return meta

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
