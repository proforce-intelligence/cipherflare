#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dark Web Multi-Engine OSINT Collector — Ultimate Edition (Dec 2025)
Combines the best of both your tools + modern async + safety filters + full analysis
Author: You (with love from a fellow builder)
"""

import asyncio
import random
import json
import csv
import uuid
import re
import hashlib
import math
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

# Optional: Tor circuit rotation
try:
    from stem import Signal
    from stem.control import Controller
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("DarkWebOSINT")

# ================================
# 2025 WORKING DARK WEB SEARCH ENGINES
# ================================
ENGINES = [
    {"name": "Torch",      "url": "http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/cgi-bin/omega/omega", "method": "POST", "data": {"P": "{q}", "DEFAULTOP": "and"}},
    {"name": "Tor66",      "url": "http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search?q={q}"},
    {"name": "Excavator",  "url": "http://2fd6cemt4gmccflhm6imvdfvli3nf7zn6rfrwpsy7uhxrgbypvwf5fad.onion/search?query={q}"},
    {"name": "AbleOnion",  "url": "http://notbumpz34bgbz4yfdigxvd6vzwtxc3zpt5imukgl6bvip2nikdmdaad.onion/search?q={q}"},
    {"name": "Ahmia",      "url": "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={q}"},
    {"name": "Haystak",    "url": "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/search.php?q={q}"},
    {"name": "DuckDuckGo", "url": "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/?q={q}"},
]

# ================================
# SAFETY & FILTERING
# ================================
TRUSTED_DOMAINS = {
    "dreadytofopooda.onion",
    "dreadisxx5x7i5n3l4q4n7h2l3o4v5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0.onion",
    "cryptbbtg65gibadeewvlm2e6bc4b7a6cog2myr6xy3v6nqfgn7tpad.onion",
    "xssforumv3isx6sq325nh6l3vefjzro4lhf4h3i7l6kgb6oz4l4z3rid.onion",
    "torbayb6ojqskcclob22hnlcwpouc4vtmksdhwirqvtf3zdc3zezskid.onion",
    "3bbad7fauom4d6sgppalyqddsqbf5u5p56b5k5uk2zxsy3d6ey2jobad.onion",
}

ILLEGAL_CP_KEYWORDS = [
    "child", "pedo", "pthc", "loli", "toddler", "rape", "torture", "abuse",
    "kids", "underage", "hebe", "cp ", "jailbait", "pedo hub", "abyss", "baby"
]

SCAM_KEYWORDS = [
    "buy ", "sell ", "shop", "store", "market", "escrow", "vendor", "deposit",
    "fullz", "cvv", "dumps", "rdp", "socks5", "smtp", "free ", "bonus", "gift",
    "telegram:", "discord:", "100% success", "guaranteed", "verified vendor"
]

# ================================
# ENTITY EXTRACTION REGEX
# ================================
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)
PGP_RE = re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----", re.S)
BTC_RE = re.compile(r"\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
ETH_RE = re.compile(r"\b(0x[a-fA-F0-9]{40})\b")
XMR_RE = re.compile(r"\b4[0-9A-Za-z]{90,110}\b")

# ================================
# UTILITY FUNCTIONS (your originals — preserved)
# ================================
def sanitize_filename(s: str) -> str:
    if not s: return "unknown"
    s = re.sub(r"^https?://", "", s, flags=re.I)
    s = s.strip().replace("/", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s[:120]

def sha1_short(s: str) -> str:
    if not s: return "unknown"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def extract_entities(text: str) -> Dict[str, List[str]]:
    if not text:
        return {"emails": [], "pgp_keys": [], "btc_addresses": [], "eth_addresses": [], "xmr_addresses": []}
    emails = list(set(EMAIL_RE.findall(text)))
    pgps = PGP_RE.findall(text)
    btc = list(set(BTC_RE.findall(text)))
    eth = list(set(ETH_RE.findall(text)))
    xmr = list(set(XMR_RE.findall(text)))
    btc_filtered = [a for a in btc if 26 <= len(a) <= 35]
    eth_filtered = [a for a in eth if len(a) == 42 and a.startswith('0x')]
    email_filtered = [e for e in emails if not any(fp in e.lower() for fp in ['example.com', 'test.com', 'localhost', 'domain.com'])]
    return {"emails": email_filtered, "pgp_keys": pgps, "btc_addresses": btc_filtered, "eth_addresses": eth_filtered, "xmr_addresses": xmr}

def find_keyword_context(text: str, keyword: str, window: int = 160) -> List[str]:
    if not keyword or not text: return []
    k = keyword.lower()
    excerpts = []
    for m in re.finditer(re.escape(k), text.lower()):
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        context = text[start:end].strip().replace("\n", " ")
        context = re.sub(r'\s+', ' ', context)
        highlighted = re.sub(f'({re.escape(keyword)})', r'**\1**', context, flags=re.IGNORECASE)
        excerpts.append(highlighted)
    unique = []
    seen = set()
    for e in excerpts:
        key = e[:50].lower()
        if key not in seen:
            unique.append(e)
            seen.add(key)
    return unique[:5]

def calculate_enhanced_risk_score(meta: dict, keyword: str = "") -> Tuple[str, float, List[str]]:
    entities = meta.get("entities", {})
    keywords_found = meta.get("keywords_found", [])
    title = meta.get("title", "").lower()
    description = meta.get("text_excerpt", "").lower()
    content = title + " " + description
    risk_score = 0.0
    indicators = []

    weights = {"btc_addresses": 25, "eth_addresses": 25, "xmr_addresses": 30, "emails": 10, "pgp_keys": 15}
    for typ, w in weights.items():
        cnt = len(entities.get(typ, []))
        if cnt:
            risk_score += w * min(math.log(cnt + 1), 3)
            indicators.append(f"{cnt} {typ.replace('_', ' ')}")

    if keywords_found:
        risk_score += min(len(keywords_found) * 5, 30)
        indicators.append(f"{len(keywords_found)} keyword matches")

    high_risk = [
        r'\b(hack|hacked|breach|dump|leak|stolen|fraud|scam|ransomware|exploit)\b',
        r'\b(drugs?|weapon|hitman|murder|money.?launder|credit.?card)\b',
        r'\b(vendor|escrow|market|shop|buy|sell|price|shipping)\b'
    ]
    matches = sum(len(re.findall(p, content, re.I)) for p in high_risk)
    if matches:
        risk_score += min(matches * 8, 40)

    if any(re.search(p, title, re.I) for p in [r'\b(child|cp|pedo|loli)\b', r'\b(zero.?day|0day|rat|botnet)\b']):
        risk_score += 50
        indicators.append("CRITICAL CONTENT DETECTED")

    risk_score = max(0, min(risk_score, 100))
    level = "critical" if risk_score >= 80 else "high" if risk_score >= 60 else "medium" if risk_score >= 30 else "low"
    indicators.insert(0, f"Risk score: {risk_score:.1f}/100")
    return level, risk_score, indicators

async def analyze_content_sentiment(content: str) -> Dict:
    if not content or len(content.strip()) < 10:
        return {"sentiment": "neutral", "threat_sentiment": "unknown"}
    c = content.lower()
    high = sum(len(re.findall(p, c)) for p in [r'\b(kill|murder|bomb|weapon|rape|pedo)\b', r'\b(threat|hack|fraud)\b'])
    total_threat = high * 3
    threat = "high" if total_threat >= 8 else "medium" if total_threat >= 4 else "low"
    return {"sentiment": "negative" if high else "neutral", "threat_sentiment": threat}

def validate_onion_url(url: str) -> bool:
    try:
        if ".onion" not in url: return False
        host = urlparse(url).hostname or ""
        if not host.endswith(".onion"): return False
        domain = host.split(".")[0]
        return len(domain) in (16, 56) and domain.isalnum() and domain.islower()
    except: return False

# ================================
# TOR IDENTITY ROTATION
# ================================
async def rotate_tor_identity():
    if not STEM_AVAILABLE:
        return
    try:
        with Controller.from_port(port=9051) as c:
            c.authenticate()
            c.signal(Signal.NEWNYM)
        await asyncio.sleep(12)
        logger.info("New Tor circuit created")
    except Exception as e:
        logger.warning(f"Failed to rotate identity: {e}")

# ================================
# CATEGORIZATION ENGINE
# ================================
def categorize_result(url: str, title: str = "", snippet: str = "") -> str:
    text = f"{url} {title} {snippet}".lower()
    domain = urlparse(url).netloc.lower()

    if any(kw in text for kw in ILLEGAL_CP_KEYWORDS):
        return "blocked_illegal"
    if domain in TRUSTED_DOMAINS:
        return "trusted_forum"
    if any(kw in text for kw in SCAM_KEYWORDS):
        return "likely_scam"
    return "unknown_potential"

# ================================
# CONTENT FETCHER + FULL ANALYSIS
# ================================
async def fetch_and_analyze(client: httpx.AsyncClient, result: Dict, keyword: str) -> Optional[Dict]:
    url = result["url"]
    try:
        resp = await client.get(url, timeout=45)
        if resp.status_code != 200:
            return None
        text = resp.text
        soup = BeautifulSoup(text, "html.parser")
        title = soup.title.string if soup.title else ""
        body = soup.get_text(separator=" ")[:15000]

        entities = extract_entities(text)
        contexts = find_keyword_context(body, keyword)
        risk_level, risk_score, indicators = calculate_enhanced_risk_score({
            "title": title,
            "text_excerpt": body[:2000],
            "entities": entities,
            "keywords_found": contexts
        }, keyword)

        sentiment = await analyze_content_sentiment(body)

        return {
            **result,
            "final_title": title or result["title"],
            "entities": entities,
            "keyword_contexts": contexts,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_indicators": indicators,
            "sentiment": sentiment["sentiment"],
            "threat_sentiment": sentiment["threat_sentiment"],
            "content_length": len(text),
            "analyzed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.debug(f"Failed to analyze {url}: {e}")
        return None

# ================================
# MAIN SEARCH + CRAWL PIPELINE
# ================================
async def search_ahmia(
    keyword: str,
    max_results: int = 400,
    rotate_identity: bool = True,
    deep_analyze: bool = True
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path("darkweb_results") / f"{keyword}_{timestamp}"
    base_dir.mkdir(parents=True, exist_ok=True)

    proxy = "socks5h://127.0.0.1:9050"
    headers = {"User-Agent": random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    ])}

    all_results = []
    seen_urls = set()

    async with httpx.AsyncClient(proxy=proxy, headers=headers, timeout=60.0, limits=httpx.Limits(max_connections=20)) as client:
        for idx, engine in enumerate(ENGINES):
            if len(all_results) >= max_results:
                break
            if rotate_identity and idx % 2 == 0:
                await rotate_tor_identity()

            try:
                url = engine["url"]
                if "{q}" in url:
                    url = url.format(q=quote_plus(keyword))

                if engine.get("method") == "POST":
                    data = {k: v.format(q=keyword) for k, v in engine.get("data", {}).items()}
                    resp = await client.post(engine["url"], data=data)
                else:
                    resp = await client.get(url)

                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href.startswith("http") or ".onion" not in href:
                        continue
                    if not validate_onion_url(href):
                        continue
                    if href in seen_urls:
                        continue

                    title = a.get_text(strip=True, separator=" ")[:300]
                    category = categorize_result(href, title)

                    if category == "blocked_illegal":
                        logger.warning(f"ILLEGAL CONTENT BLOCKED: {href}")
                        continue

                    result = {
                        "id": str(uuid.uuid4()),
                        "url": href,
                        "title": title,
                        "engine": engine["name"],
                        "category": category,
                        "discovered_at": datetime.now().isoformat()
                    }
                    all_results.append(result)
                    seen_urls.add(href)

            except Exception as e:
                logger.warning(f"{engine['name']} failed: {e}")

            await asyncio.sleep(random.uniform(9, 17))

    # Save raw discovery
    raw_path = base_dir / "0_discovered_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Deep analysis phase
    analyzed = []
    if deep_analyze and all_results:
        logger.info(f"Starting deep analysis on {len(all_results)} URLs...")
        semaphore = asyncio.Semaphore(8)

        async def bounded_analyze(res):
            async with semaphore:
                return await fetch_and_analyze(client, res, keyword)

        tasks = [bounded_analyze(r) for r in all_results[:max_results]]
        analyzed = [r for r in await asyncio.gather(*tasks) if r]

    # Final save
    final_path = base_dir / "FINAL_ANALYZED.json"
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(analyzed or all_results, f, indent=2, ensure_ascii=False)

    summary = {
        "keyword": keyword,
        "total_discovered": len(all_results),
        "analyzed": len(analyzed),
        "categories": {cat: len([r for r in all_results if r["category"] == cat]) for cat in ["trusted_forum", "likely_scam", "unknown_potential"]},
        "output_dir": str(base_dir)
    }
    with open(base_dir / "SUMMARY.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"COMPLETE → {base_dir}")
    return base_dir

import asyncio
import random

async def random_delay(min_sec: float = 1.0, max_sec: float = 4.0) -> None:
    """Async sleep with random delay to avoid detection"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))
# ================================
# CLI ENTRYPOINT
# ================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dark Web Multi-Engine OSINT Pro (2025)")
    parser.add_argument("keyword", help="Search keyword")
    parser.add_argument("--max", type=int, default=400, help="Max results (default: 400)")
    parser.add_argument("--no-rotate", action="store_true", help="Disable Tor identity rotation")
    parser.add_argument("--no-analyze", action="store_true", help="Skip deep content analysis")
    args = parser.parse_args()

    print("\n" + "="*80)
    print(f" DARK WEB OSINT PRO — SEARCHING: {args.keyword.upper()}")
    print("="*80 + "\n")

    asyncio.run(search_ahmia(
        keyword=args.keyword,
        max_results=args.max,
        rotate_identity=not args.no_rotate,
        deep_analyze=not args.no_analyze
    ))
