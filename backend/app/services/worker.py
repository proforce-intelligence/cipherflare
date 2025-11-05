import asyncio
import json
from aiokafka import AIOKafkaConsumer
from app.services.dark_web_scraper import search_ahmia, scrape_onion_page, internal_links_for_domain, rotate_tor_identity
from app.services.es_client import index_finding
from app.models.dark_web import DarkWebResult
from pathlib import Path
from playwright.async_api import async_playwright
import os
import random

async def process_job(msg):
    payload = json.loads(msg.value.decode("utf-8"))
    job_id = payload["job_id"]
    out_dir = Path("/app/dark_web_files") / job_id
    out_dir.mkdir(exist_ok=True)
    
    pw = await async_playwright().start()
    
    if payload["type"] == "ad_hoc":
        onion_links = search_ahmia(payload["keyword"], payload["max_results"])
        for link in onion_links:
            ok, msg = rotate_tor_identity()
            await asyncio.sleep(random.uniform(2.0, 5.0))
            meta, _ = await scrape_onion_page(pw, link, out_dir, payload["keyword"])
            # Risk level (your logic)
            risk_level = "low"
            if len(meta["entities"].get("btc_addresses", [])) > 0:
                risk_level = "high"
            # ...
            result = DarkWebResult(**meta, risk_level=risk_level)
            await index_finding(result.dict())
    
    elif payload["type"] == "monitor":
        ok, msg = rotate_tor_identity()
        meta, _ = await scrape_onion_page(pw, payload["url"], out_dir)
        result = DarkWebResult(**meta)
        await index_finding(result.dict())
    
    await pw.stop()

async def main():
    consumer = AIOKafkaConsumer(
        "ad_hoc_jobs", "monitor_jobs",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    )
    await consumer.start()
    async for msg in consumer:
        await process_job(msg)
        await consumer.commit()

if __name__ == "__main__":
    asyncio.run(main())