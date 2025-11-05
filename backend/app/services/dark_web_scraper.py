#!/usr/bin/env python3
"""
Your original code - minor mods: 
- Use /app/dark_web_files for outputs
- Exposed functions for worker
- Removed run_session (refactored to worker)
- Kept all else as-is
"""

import os
import re
import json
import time
import asyncio
import random
import hashlib
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from playwright.async_api import async_playwright

try:
    from stem import Signal
    from stem.control import Controller
    STEM_AVAILABLE = True
except Exception:
    STEM_AVAILABLE = False

try:
    from langdetect import detect as detect_lang
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False

load_dotenv()

TOR_SOCKS = os.getenv("TOR_SOCKS", "127.0.0.1:9050")
TOR_CONTROL = os.getenv("TOR_CONTROL", "")
TOR_CONTROL_PASS = os.getenv("TOR_CONTROL_PASS", "")
CONCURRENCY = int(os.getenv("CONCURRENCY", "1"))
DEFAULT_DEPTH = int(os.getenv("DEPTH", "0"))

OUTPUT_BASE = Path("/app/dark_web_files")  # Shared volume
OUTPUT_BASE.mkdir(exist_ok=True)

def ts():
    return time.strftime("%Y%m%d-%H%M%S")

def sanitize_filename(s: str) -> str:
    if not s:
        return "unknown"
    s = re.sub(r"^https?://", "", s, flags=re.I)
    s = s.strip().replace("/", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s[:120]

def build_tor_proxies():
    return {
        "http": f"socks5h://{TOR_SOCKS}",
        "https": f"socks5h://{TOR_SOCKS}",
    }

def sha1_short(s: str) -> str:
    if not s:
        return "unknown"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)
PGP_RE = re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----", re.S)
BTC_RE = re.compile(r"\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
ETH_RE = re.compile(r"\b(0x[a-fA-F0-9]{40})\b")
XMR_RE = re.compile(r"\b4[0-9A-Za-z]{90,110}\b")

def rotate_tor_identity():
    if not STEM_AVAILABLE or not TOR_CONTROL:
        return False, "Stem or TOR_CONTROL not configured"
    try:
        host, port = TOR_CONTROL.split(":")
        with Controller.from_port(address=host, port=int(port)) as c:
            if TOR_CONTROL_PASS:
                c.authenticate(password=TOR_CONTROL_PASS)
            else:
                c.authenticate()
            c.signal(Signal.NEWNYM)
        return True, "NEWNYM signal sent"
    except Exception as e:
        return False, f"Failed NEWNYM: {e}"

def clean_onion_links(raw_links):
    cleaned = []
    for link in raw_links:
        if not link:
            continue
        if "/search/redirect?" in link:
            qs = parse_qs(urlparse(link).query)
            if "redirect_url" in qs:
                onion_url = unquote(qs["redirect_url"][0])
                cleaned.append(onion_url)
        elif ".onion" in link:
            cleaned.append(link)
    return cleaned

def search_ahmia(keyword: str, max_results: int = 10, timeout: int = 40):
    from urllib.parse import quote_plus
    base = "https://ahmia.fi/search/?q="
    url = base + quote_plus(keyword)
    proxies = build_tor_proxies()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    raw_links = [a.get("href", "").strip() for a in soup.select("a[href]")]
    onion_links = clean_onion_links(raw_links)

    seen, final = set(), []
    for link in onion_links:
        if link not in seen:
            final.append(link)
            seen.add(link)
        if len(final) >= max_results:
            break

    return final

def extract_meta_from_html(html: str, base_url: str = "") -> dict:
    if not html:
        return {"title": "", "meta_description": "", "meta_keywords": "", "links": []}
    
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = (soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"}))["content"].strip() if (soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})) else ""
    meta_keywords = soup.find("meta", attrs={"name": "keywords"})["content"].strip() if soup.find("meta", attrs={"name": "keywords"}) else ""
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if href:
            if base_url and not href.startswith("http"):
                href = urljoin(base_url, href)
            links.append(href)
    return {"title": title, "meta_description": meta_desc, "meta_keywords": meta_keywords, "links": links}

def find_keyword_context(text: str, keyword: str, window: int = 160) -> list:
    if not keyword or not text:
        return []
    k = keyword.lower()
    excerpts = []
    for m in re.finditer(re.escape(k), text.lower()):
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        excerpts.append(text[start:end].strip().replace("\n", " "))
    return list(set(excerpts))

def extract_entities(text: str) -> dict:
    if not text:
        return {"emails": [], "pgp_keys": [], "btc_addresses": [], "eth_addresses": [], "xmr_addresses": []}
    emails = list(set(EMAIL_RE.findall(text)))
    pgps = PGP_RE.findall(text)
    btc = list(set(BTC_RE.findall(text)))
    eth = list(set(ETH_RE.findall(text)))
    xmr = list(set(XMR_RE.findall(text)))
    return {"emails": emails, "pgp_keys": pgps, "btc_addresses": btc, "eth_addresses": eth, "xmr_addresses": xmr}

async def scrape_onion_page(playwright, url: str, out_dir: Path, keyword: str = "", depth: int = 0):
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
        "scraped_at": ts(),
        "ok": False,
        "error": None,
        "title": None,
        "meta_description": None,
        "meta_keywords": None,
        "language": None,
        "keywords_found": [],
        "text_excerpt": None,
        "entities": {},
        "links": [],
        "raw_html_file": None,
        "screenshot_file": None,
        "text_file": None,
        "depth": depth
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(1.0, 2.5))
        for _ in range(random.randint(3, 7)):
            await page.mouse.wheel(0, random.randint(300, 1000))
            await asyncio.sleep(random.uniform(0.6, 1.6))

        raw_html = await page.content() or await page.evaluate("() => document.documentElement.outerHTML")

        if raw_html:
            html_path = site_dir / f"{safe_name}.html"
            html_path.write_text(raw_html, encoding="utf-8", errors="replace")
            meta["raw_html_file"] = str(html_path)

        shot_path = site_dir / f"{safe_name}.png"
        await page.screenshot(path=str(shot_path), full_page=True)
        meta["screenshot_file"] = str(shot_path)

        visible_text = await page.inner_text("body") or await page.evaluate("() => document.body ? document.body.innerText : ''")

        if visible_text:
            text_path = site_dir / f"{safe_name}.txt"
            text_path.write_text(visible_text, encoding="utf-8", errors="replace")
            meta["text_file"] = str(text_path)

        parsed = extract_meta_from_html(raw_html, base_url=url)
        meta.update(parsed)

        entities = extract_entities(visible_text + "\n" + raw_html)
        meta["entities"] = entities

        if LANGDETECT_AVAILABLE and visible_text.strip():
            meta["language"] = detect_lang(visible_text) or "unknown"

        if keyword and visible_text:
            contexts = find_keyword_context(visible_text, keyword, 200)
            meta["keywords_found"] = contexts
            meta["text_excerpt"] = contexts[0] if contexts else None
            freq = len(re.findall(re.escape(keyword), visible_text, re.I))
            meta["relevance_score"] = round(freq / max(1, len(visible_text)) * 10000, 4)

        meta["ok"] = True

    except Exception as e:
        meta["error"] = str(e)

    finally:
        meta_path = site_dir / "meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        await context.close()
        await browser.close()
        return meta, site_dir

def internal_links_for_domain(links: list, domain: str):
    out = []
    for l in links:
        if not l:
            continue
        lp = urlparse(l)
        if lp.netloc and domain in lp.netloc:
            out.append(l)
    return out