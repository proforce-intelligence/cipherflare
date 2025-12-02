import re
import hashlib
import asyncio
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import math
import logging
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import quote_plus, urlparse
import time

# Optional: Tor control for NEWNYM
try:
    from stem import Signal
    from stem.control import Controller
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False

logger = logging.getLogger(__name__)

# Regex patterns for entity extraction
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)
PGP_RE = re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----", re.S)
BTC_RE = re.compile(r"\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
ETH_RE = re.compile(r"\b(0x[a-fA-F0-9]{40})\b")
XMR_RE = re.compile(r"\b4[0-9A-Za-z]{90,110}\b")

def sanitize_filename(s: str) -> str:
    """Turn title/URL into filesystem-safe short name."""
    if not s:
        return "unknown"
    s = re.sub(r"^https?://", "", s, flags=re.I)
    s = s.strip().replace("/", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s[:120]

def sha1_short(s: str) -> str:
    """Generate short SHA1 hash"""
    if not s:
        return "unknown"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract crypto addresses, emails, and PGP keys from text"""
    if not text:
        return {
            "emails": [],
            "pgp_keys": [],
            "btc_addresses": [],
            "eth_addresses": [],
            "xmr_addresses": []
        }
    
    emails = list(set(EMAIL_RE.findall(text)))
    pgps = PGP_RE.findall(text)
    btc = list(set(BTC_RE.findall(text)))
    eth = list(set(ETH_RE.findall(text)))
    xmr = list(set(XMR_RE.findall(text)))
    
    # Filter Bitcoin addresses
    btc_filtered = [addr for addr in btc if 26 <= len(addr) <= 35]
    
    # Filter Ethereum addresses
    eth_filtered = [addr for addr in eth if len(addr) == 42 and addr.startswith('0x')]
    
    # Filter emails
    email_filtered = [
        email for email in emails
        if not any(fp in email.lower() for fp in ['example.com', 'test.com', 'localhost', 'domain.com'])
        and '@' in email and '.' in email.split('@')[1]
    ]
    
    return {
        "emails": email_filtered,
        "pgp_keys": pgps,
        "btc_addresses": btc_filtered,
        "eth_addresses": eth_filtered,
        "xmr_addresses": xmr
    }

def find_keyword_context(text: str, keyword: str, window: int = 160) -> List[str]:
    """Return list of small excerpts where keyword appears"""
    if not keyword or not text:
        return []
    
    k = keyword.lower()
    excerpts = []
    
    for m in re.finditer(re.escape(k), text.lower()):
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        context = text[start:end].strip().replace("\n", " ")
        context = re.sub(r'\s+', ' ', context)
        
        highlighted_context = re.sub(
            f'({re.escape(keyword)})',
            r'**\1**',
            context,
            flags=re.IGNORECASE
        )
        excerpts.append(highlighted_context)
    
    # Deduplicate
    unique_excerpts = []
    seen = set()
    for excerpt in excerpts:
        key = excerpt[:50].lower()
        if key not in seen:
            unique_excerpts.append(excerpt)
            seen.add(key)
    
    return unique_excerpts[:5]

def calculate_enhanced_risk_score(meta: dict, keyword: str = "") -> Tuple[str, float, List[str]]:
    """Calculate risk level, score, and threat indicators"""
    entities = meta.get("entities", {})
    keywords_found = meta.get("keywords_found", [])
    title = meta.get("title", "").lower()
    description = meta.get("text_excerpt", "").lower()
    content = title + " " + description
    
    risk_score = 0.0
    threat_indicators = []
    
    # Entity-based scoring
    entity_weights = {
        "btc_addresses": 25,
        "eth_addresses": 25,
        "xmr_addresses": 30,
        "emails": 10,
        "pgp_keys": 15
    }
    
    for entity_type, weight in entity_weights.items():
        entity_count = len(entities.get(entity_type, []))
        if entity_count > 0:
            entity_score = weight * min(math.log(entity_count + 1), 3)
            risk_score += entity_score
            threat_indicators.append(f"{entity_count} {entity_type.replace('_', ' ')}")
    
    # Keyword context scoring
    keyword_score = len(keywords_found) * 5
    if keyword_score > 0:
        risk_score += min(keyword_score, 30)
        threat_indicators.append(f"{len(keywords_found)} keyword matches")
    
    # High-risk patterns
    high_risk_patterns = [
        r'\b(hack|hacking|hacked|breach|breached|dump|dumped|leak|leaked)\b',
        r'\b(stolen|fraud|scam|phishing|malware|ransomware|exploit)\b',
        r'\b(drugs?|weapon|weapons|hitman|murder|assassination)\b',
        r'\b(money.?launder|credit.?card|bank.?account|paypal.?hack)\b',
        r'\b(bitcoin.?mixer|crypto.?tumbl|anonymous.?payment)\b',
        r'\b(database|db.?dump|sql.?injection|admin.?panel|backdoor)\b',
        r'\b(password|credential|login|account.?dump)\b',
        r'\b(vendor|escrow|market|shop|store|buy|sell|price)\b',
        r'\b(shipping|delivery|stealth|discrete|anonymous)\b'
    ]
    
    pattern_matches = 0
    for pattern in high_risk_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            pattern_matches += len(matches)
            threat_indicators.extend([f"High-risk term: {match}" for match in matches[:3]])
    
    if pattern_matches > 0:
        pattern_score = min(pattern_matches * 8, 40)
        risk_score += pattern_score
    
    # Critical title indicators
    critical_patterns = [
        r'\b(zero.?day|0.?day|exploit.?kit|rat|trojan|botnet)\b',
        r'\b(child|cp|illegal|terrorist|bomb|weapon)\b'
    ]
    
    for pattern in critical_patterns:
        if re.search(pattern, title, re.IGNORECASE):
            risk_score += 50
            threat_indicators.append("Critical content detected")
            break
    
    # Content length analysis
    if description:
        if len(description) < 50:
            risk_score -= 10
            threat_indicators.append("Minimal content")
        elif len(description) > 1000 and sum(len(entities.get(k, [])) for k in entities) > 5:
            risk_score += 15
            threat_indicators.append("Extensive content with entities")
    
    # Normalize score
    risk_score = max(0, min(risk_score, 100))
    
    # Determine risk level
    if risk_score >= 80 or any("Critical" in ind for ind in threat_indicators):
        risk_level = "critical"
    elif risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 30:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    threat_indicators.insert(0, f"Risk score: {risk_score:.1f}/100")
    
    return risk_level, risk_score, threat_indicators

async def analyze_content_sentiment(content: str) -> Dict:
    """Analyze sentiment and threat level of content"""
    if not content or len(content.strip()) < 10:
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "emotional_indicators": [],
            "threat_sentiment": "unknown"
        }
    
    try:
        content_lower = content.lower()
        
        # Pattern detection
        high_threat = sum(len(re.findall(p, content_lower)) for p in [
            r'\b(kill|murder|death|bomb|weapon|gun|knife|violence)\b',
            r'\b(threat|threaten|harm|hurt|destroy|eliminate)\b',
            r'\b(hack|breach|steal|fraud|scam|illegal|criminal|drug)\b'
        ])
        
        medium_threat = sum(len(re.findall(p, content_lower)) for p in [
            r'\b(angry|rage|furious|hate|revenge)\b',
            r'\b(secret|hidden|covert|underground)\b',
            r'\b(money|bitcoin|payment|buy|sell)\b'
        ])
        
        negative = sum(len(re.findall(p, content_lower)) for p in [
            r'\b(bad|terrible|awful|horrible|disgusting)\b',
            r'\b(fear|scared|panic|terror|anxiety)\b',
            r'\b(sad|depressed|hopeless|desperate)\b'
        ])
        
        positive = sum(len(re.findall(p, content_lower)) for p in [
            r'\b(good|great|excellent|amazing)\b',
            r'\b(love|like|enjoy|happy|joy)\b',
            r'\b(help|support|care|protect)\b'
        ])
        
        total_threat = (high_threat * 3) + (medium_threat * 2)
        
        if total_threat >= 8 or high_threat >= 3:
            threat_sentiment = "high"
        elif total_threat >= 4:
            threat_sentiment = "medium"
        else:
            threat_sentiment = "low"
        
        total_negative = negative + (high_threat * 2) + medium_threat
        
        if total_negative > positive * 1.5:
            sentiment = "negative"
        elif positive > total_negative * 1.5:
            sentiment = "positive"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "confidence": min(0.9, total_negative / max(len(content.split()) / 10, 1)),
            "emotional_indicators": [
                f"High threat: {high_threat}" if high_threat > 0 else None,
                f"Medium threat: {medium_threat}" if medium_threat > 0 else None,
                f"Negative: {negative}" if negative > 0 else None
            ],
            "threat_sentiment": threat_sentiment
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "emotional_indicators": [],
            "threat_sentiment": "unknown"
        }

async def random_delay(min_sec: float = 1, max_sec: float = 3):
    """Random async delay to avoid rate limiting"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)

def validate_onion_url(url: str) -> bool:
    """
    Validate that URL is a properly formatted .onion address.
    Ensures URLs match v2 (16 chars) or v3 (56 chars) onion formats.
    """
    try:
        if ".onion" not in url:
            return False
        
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        
        if not hostname:
            return False
        
        parts = hostname.split(".")
        if len(parts) < 2 or parts[-1] != "onion":
            return False
        
        domain = parts[0]
        
        # Validate: must be alphanumeric lowercase only
        if not all(c.isalnum() and (c.islower() or c.isdigit()) for c in domain):
            return False
        
        # Must be v2 (16 chars) or v3 (56 chars)
        domain_len = len(domain)
        return domain_len == 16 or domain_len == 56
    
    except Exception as e:
        logger.warning(f"URL validation failed for {url}: {e}")
        return False

def search_ahmia(keyword: str, max_results: int = 50) -> List[str]:
    """
    Search Torch darkweb search engine for .onion URLs matching keyword.
    Torch is at: http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion
    Falls back to Ahmia.fi if Torch is unreachable.
    
    Args:
        keyword: Search term to find in dark web
        max_results: Maximum .onion URLs to return (capped at 200)
    
    Returns:
        List of valid .onion URLs found matching the keyword
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from urllib3.contrib.socks import SOCKSProxyManager
    import certifi
    
    onion_links = []
    max_results = min(max_results, 200)
    
    torch_url = "http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion"
    
    # User agents for avoiding detection
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1"
    }
    
    try:
        import socket
        socket.create_connection(("127.0.0.1", 9050), timeout=2)
        logger.info("[✓] Tor SOCKS proxy is accessible on 127.0.0.1:9050")
    except Exception as e:
        logger.error(f"[!] Tor SOCKS proxy NOT accessible: {e}")
        logger.info("[*] Make sure Tor is running: 'tor' or 'sudo systemctl start tor'")
        logger.info("[*] Skipping Torch search, trying Ahmia fallback only")
    
    # Try Torch search first via Tor SOCKS proxy
    try:
        logger.info(f"[*] Searching Torch for keyword: {keyword}")
        search_url = f"{torch_url}/?q={quote_plus(keyword)}"
        
        session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        
        # Mount SOCKS proxy with remote DNS resolution
        socks_adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", socks_adapter)
        session.mount("https://", socks_adapter)
        
        response = session.get(
            search_url,
            timeout=20,
            proxies={
                "http": "socks5h://127.0.0.1:9050",  # Use socks5h for remote DNS
                "https": "socks5h://127.0.0.1:9050"
            },
            headers=headers,
            verify=False
        )
        
        logger.info(f"[✓] Torch responded with status {response.status_code}")
        
        if response.status_code == 200 and len(response.text) > 100:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Parse Torch search results - try multiple possible selectors
            for selector in ["div.result", "li.result", "div.search-result", "div.resultwrapper"]:
                results = soup.find_all(selector)
                if results:
                    logger.info(f"[*] Found {len(results)} results using selector: {selector}")
                    break
            else:
                results = []
                logger.warning(f"[!] Could not find results with any selector, trying all links")
                results = soup.find_all("a")
            
            for result_elem in results:
                if len(onion_links) >= max_results:
                    break
                
                # Extract link from result
                link_elem = result_elem if result_elem.name == "a" else result_elem.find("a")
                if link_elem and link_elem.get("href"):
                    url = link_elem.get("href", "").strip()
                    
                    # Clean and validate URL
                    if ".onion" in url and validate_onion_url(url):
                        if not url.startswith("http"):
                            url = "http://" + url
                        onion_links.append(url)
                        logger.debug(f"[+] Found valid onion URL: {url}")
            
            if onion_links:
                logger.info(f"[✓] Torch returned {len(onion_links)} valid results for '{keyword}'")
                return onion_links
            else:
                logger.warning(f"[!] Torch returned {len(results)} results but none were valid .onion URLs")
        else:
            logger.warning(f"[!] Torch returned empty response (status {response.status_code})")
    
    except requests.exceptions.ProxyError as e:
        logger.warning(f"[!] Tor SOCKS proxy error (is Tor running?): {str(e)}")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"[!] Connection error (DNS resolution failed through Tor): {str(e)}")
    except requests.exceptions.Timeout as e:
        logger.warning(f"[!] Torch search timeout: {str(e)}")
    except Exception as e:
        logger.warning(f"[!] Torch search failed: {str(e)}")
    
    # Fallback to Ahmia.fi search via clearnet
    try:
        logger.info(f"[*] Falling back to Ahmia search for keyword: {keyword}")
        ahmia_url = "https://ahmia.fi/search/"
        params = {"q": keyword}
        
        session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        
        response = session.get(
            ahmia_url,
            params=params,
            timeout=15,
            headers=headers,
            verify=certifi.where()
        )
        
        logger.info(f"[✓] Ahmia responded with status {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Parse Ahmia results
            for result_div in soup.find_all("div", class_="resultwrapper"):
                if len(onion_links) >= max_results:
                    break
                
                title_elem = result_div.find("h4", class_="title")
                if not title_elem:
                    continue
                
                link_elem = title_elem.find("a")
                if not link_elem or not link_elem.get("href"):
                    continue
                
                url = link_elem.get("href", "").strip()
                
                if ".onion" in url and validate_onion_url(url):
                    if not url.startswith("http"):
                        url = "http://" + url
                    onion_links.append(url)
                    logger.debug(f"[+] Found valid onion URL: {url}")
            
            if onion_links:
                logger.info(f"[✓] Ahmia returned {len(onion_links)} valid results for '{keyword}'")
                return onion_links
            else:
                logger.warning(f"[!] Ahmia returned no valid .onion URLs for '{keyword}'")
        else:
            logger.warning(f"[!] Ahmia returned status {response.status_code}")
    
    except Exception as e:
        logger.warning(f"[!] Ahmia search failed: {str(e)}")
    
    logger.warning(f"[!] Could not find any results for '{keyword}' via Torch or Ahmia")
    return []