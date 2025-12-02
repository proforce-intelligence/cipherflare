#!/usr/bin/env python3
"""
Dark Web Scraper Worker - Consumes Kafka jobs and indexes to Elasticsearch
Run with: python -m app.services.worker
"""

import asyncio
import logging
import os
import sys
import re
from pathlib import Path
from datetime import datetime
import uuid

# Playwright for scraping
from playwright.async_api import async_playwright, Page

# Our services
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
    search_ahmia  # Import search_ahmia directly at module level
)
from app.services.tor_manager import TorManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOR_SOCKS = os.getenv("TOR_SOCKS", "127.0.0.1:9050")
OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE", "./dark_web_results"))
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

class DarkWebWorker:
    def __init__(self):
        self.es_client = ESClient(ES_URL)
        self.tor_manager = TorManager(TOR_SOCKS)
        self.consumer = KafkaConsumer(
            topics=["ad_hoc_jobs", "monitor_jobs"],
            bootstrap_servers=KAFKA_BOOTSTRAP
        )
        self.status_producer = KafkaProducerConsumer(KAFKA_BOOTSTRAP)
        self.output_base = OUTPUT_BASE
        self.output_base.mkdir(parents=True, exist_ok=True)
    
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
        max_results = payload.get("max_results", 50)
        user_id = payload.get("user_id")
        
        try:
            logger.info(f"[*] Starting ad_hoc search for keyword: {keyword}")
            
            onion_links = search_ahmia(keyword, max_results=max_results)
            logger.info(f"[*] Found {len(onion_links)} onion links")
            
            if not onion_links:
                await self.status_producer.send_status(job_id, "COMPLETED", {
                    "findings_count": 0,
                    "reason": "No links found"
                })
                return
            
            # Create session directory
            session_dir = self.output_base / f"{sanitize_filename(keyword)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Scrape each link
            findings = []
            async with async_playwright() as pw:
                for idx, link in enumerate(onion_links[:max_results], 1):
                    try:
                        await random_delay(2, 5)
                        
                        logger.info(f"[+] Scraping ({idx}/{len(onion_links[:max_results])}): {link}")
                        
                        if not validate_onion_url(link):
                            logger.warning(f"[!] Invalid .onion URL format, skipping: {link}")
                            continue
                        
                        meta = await self.scrape_onion_page(
                            pw, link, session_dir, keyword
                        )
                        
                        if meta.get("ok"):
                            # Calculate risk and sentiment
                            risk_level, risk_score, threat_indicators = calculate_enhanced_risk_score(meta, keyword)
                            sentiment = await analyze_content_sentiment(
                                meta.get("title", "") + " " + meta.get("text_excerpt", "")
                            )
                            
                            # Prepare finding for ES
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
                                "user_id": user_id
                            }
                            
                            # Index to Elasticsearch
                            await self.es_client.index_finding(finding)
                            findings.append(finding)
                            logger.info(f"[✓] Indexed: {link} (risk: {risk_level})")
                        
                        await random_delay(1, 3)
                    
                    except Exception as e:
                        logger.error(f"[!] Failed to scrape {link}: {e}")
                        continue
            
            logger.info(f"[✓] Ad-hoc job {job_id} completed: {len(findings)} findings")
            await self.status_producer.send_status(job_id, "COMPLETED", {
                "findings_count": len(findings)
            })
        
        except Exception as e:
            logger.error(f"[!] Ad-hoc job failed: {e}")
            await self.status_producer.send_status(job_id, "FAILED", {
                "error": str(e)
            })
    
    async def handle_monitor(self, job_id: str, payload: dict):
        """Handle targeted URL monitoring job"""
        url = payload.get("target_url") or payload.get("url")
        user_id = payload.get("user_id")
        
        try:
            logger.info(f"[*] Starting monitor scrape for URL: {url}")
            
            async with async_playwright() as pw:
                meta = await self.scrape_onion_page(pw, url, self.output_base, "")
                
                if meta.get("ok"):
                    risk_level, risk_score, threat_indicators = calculate_enhanced_risk_score(meta)
                    sentiment = await analyze_content_sentiment(
                        meta.get("title", "") + " " + meta.get("text_excerpt", "")
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
                        "user_id": user_id
                    }
                    
                    await self.es_client.index_finding(finding)
                    logger.info(f"[✓] Monitor job {job_id} completed")
                    
                    await self.status_producer.send_status(job_id, "COMPLETED", {
                        "findings_count": 1,
                        "risk_level": risk_level
                    })
        
        except Exception as e:
            logger.error(f"[!] Monitor job failed: {e}")
            await self.status_producer.send_status(job_id, "FAILED", {
                "error": str(e)
            })
    
    async def scrape_onion_page(self, playwright, url: str, out_dir: Path, keyword: str = ""):
        """Scrape .onion URL and return metadata"""
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
            "title": None,
            "text_excerpt": None,
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
            
            # Save HTML
            if raw_html:
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
            
            # Save text
            if visible_text:
                text_path = site_dir / f"{safe_name}.txt"
                text_path.write_text(visible_text, encoding="utf-8", errors="replace")
                meta["text_file"] = str(text_path)
                meta["text_excerpt"] = visible_text[:500]
            
            # Extract title
            try:
                title_elem = await page.query_selector("title")
                if title_elem:
                    meta["title"] = await title_elem.inner_text()
            except:
                pass
            
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
            logger.info(f"[✓] Scraped {url}")
        
        except Exception as e:
            meta["error"] = str(e)
            logger.error(f"[!] Scrape error for {url}: {e}")
        
        finally:
            await context.close()
            await browser.close()
            return meta
    
    async def run(self):
        """Start consuming and processing messages"""
        try:
            await self.consumer.connect()
            await self.status_producer.connect()
            logger.info("[✓] Worker started")
            
            await self.consumer.consume(self.process_message)
        
        except Exception as e:
            logger.error(f"[!] Worker error: {e}")
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
        logger.info("[!] Worker interrupted")
