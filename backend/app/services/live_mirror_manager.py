# """
# Live Mirror Manager - Manages active browser sessions for live mirroring
# with history, diff & AI-powered content analysis
# """
# 
# import asyncio
# import logging
# import uuid
# import json
# import base64
# from datetime import datetime, timezone
# from typing import Dict, Optional, List, Any
# 
# from dataclasses import dataclass
# from playwright.async_api import async_playwright, Browser, BrowserContext, Page
# 
# import ollama
# 
# logger = logging.getLogger(__name__)
# 
# 
# @dataclass
# class Snapshot:
#     """Represents a single captured state of the page"""
#     id: int
#     timestamp: datetime
#     html: str
#     text: str
#     screenshot_base64: str
#     current_url: str
#     title: str
# 
# 
# class LiveMirrorSession:
#     """Represents an active live mirror session with history & AI analysis"""
# 
#     def __init__(self, session_id: str, user_id: str, target_url: str, tor_socks: str):
#         self.session_id = session_id
#         #self.user_id = user_id
#         self.target_url = target_url
#         self.tor_socks = tor_socks
#         self.browser: Optional[Browser] = None
#         self.context: Optional[BrowserContext] = None
#         self.page: Optional[Page] = None
#         self.is_active = True
#         self.last_activity = datetime.now(timezone.utc)
#         self.page_views = 0
#         self.screenshots_taken = 0
# 
#         self.snapshots: List[Snapshot] = []
#         self._next_snapshot_id: int = 1
# 
#     async def _capture_and_save_snapshot(self) -> Snapshot:
#         """Internal method: Captures current page state and saves it to history"""
#         if not self.page:
#             raise RuntimeError("No active page")
# 
#         html = await self.page.content()
#         text = await self.page.evaluate("() => document.body ? document.body.innerText : ''")
#         screenshot_bytes = await self.page.screenshot(type="png", full_page=True)
#         screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
# 
#         snapshot = Snapshot(
#             id=self._next_snapshot_id,
#             timestamp=datetime.now(timezone.utc),
#             html=html,
#             text=text,
#             screenshot_base64=screenshot_base64,
#             current_url=self.page.url,
#             title=await self.page.title()
#         )
# 
#         self.snapshots.append(snapshot)
#         self._next_snapshot_id += 1
#         self.screenshots_taken += 1
#         self.last_activity = datetime.now(timezone.utc)
# 
#         return snapshot
# 
#     async def _analyze_content(self, text: str) -> Dict[str, Any]:
#         """
#         Analyze page text using local LLM (Ollama + Llama 3.1)
#         Returns structured analysis: summary, entities, keywords, risk score, alerts
#         """
#         if not text.strip():
#             return {
#                 "summary": "No readable text content on this page",
#                 "entities": [],
#                 "keywords_found": [],
#                 "risk_score": 0,
#                 "alerts": []
#             }
# 
#         prompt = f"""
# You are a dark web threat intelligence analyst.
# Analyze the following page content from a .onion site:
# 
# {text[:12000]}
# 
# Tasks:
# 1. Write a concise summary (2-4 sentences) of what the page is about.
# 2. Extract key entities: people names, organizations, companies, cryptocurrencies (BTC/XMR addresses), emails, domains, phone numbers.
# 3. Detect these suspicious keywords/phrases (only return matches):
#    - leak, dump, database, breach, credentials, password, credit card
#    - ransomware, malware, exploit, 0day, cve, hacking, ddos
#    - buy, sell, vendor, shop, market, escrow, carding
#    - hitman, assassin, murder, kill, weapon
#    - child, cp, porn, underage, lolita
#    - bitcoin, monero, xmr, wallet, crypto
# 4. Calculate a risk score (0-100):
#    - 80-100: Clear illegal activity (markets, leaks, threats, CSAM)
#    - 50-79: Suspicious (hacking forums, carding mentions)
#    - 20-49: Potentially risky (dark web forums, privacy tools)
#    - 0-19: Low risk (news, blogs, normal discussion)
# 
# CRITICAL RULES:
# - Output **ONLY** valid JSON. Nothing else.
# - No explanations, no markdown, no code blocks, no "Here is the JSON:", no ```json tags.
# - The JSON must be directly parseable with json.loads().
# - Use this exact structure, even if some fields are empty:
# 
# {{
#   "summary": "short summary here",
#   "entities": ["entity1", "entity2"],
#   "keywords_found": ["keyword1", "keyword2"],
#   "risk_score": 85,
#   "alerts": ["High risk: leaked credentials detected"]
# }}
# 
# Page content:
# {text[:12000]}
# """
# 
#         try:
#             # Run Ollama in a thread (non-blocking)
#             response = await asyncio.to_thread(
#                 ollama.generate,
#                 model="llama3.1:8b",
#                 prompt=prompt,
#                 options={"temperature": 0.0, "num_predict": 1024}  # zero temp + more tokens
#             )
# 
#             raw_response = response['response'].strip()
# 
#             # === Robust JSON extraction: try to find and parse the JSON block ===
#             start_idx = raw_response.find('{')
#             end_idx = raw_response.rfind('}') + 1
# 
#             if start_idx != -1 and end_idx > start_idx:
#                 json_str = raw_response[start_idx:end_idx]
#                 try:
#                     analysis = json.loads(json_str)
# 
#                     # Ensure all expected keys exist (with safe defaults)
#                     defaults = {
#                         "summary": "",
#                         "entities": [],
#                         "keywords_found": [],
#                         "risk_score": 0,
#                         "alerts": []
#                     }
#                     for key, default in defaults.items():
#                         if key not in analysis:
#                             analysis[key] = default
#                         elif key == "risk_score" and not isinstance(analysis[key], (int, float)):
#                             analysis[key] = 0
# 
#                     return analysis
# 
#                 except json.JSONDecodeError as parse_err:
#                     logger.warning(
#                         f"[LiveMirror] JSON parse failed for session {self.session_id}: "
#                         f"{str(parse_err)} | Raw response snippet: {raw_response[:300]}..."
#                     )
#             else:
#                 logger.warning(
#                     f"[LiveMirror] No JSON block found in Ollama response for session {self.session_id}: "
#                     f"Raw response snippet: {raw_response[:300]}..."
#                 )
# 
#             # Fallback if parsing failed
#             return {
#                 "summary": "Analysis failed - invalid LLM response format",
#                 "entities": [],
#                 "keywords_found": [],
#                 "risk_score": 0,
#                 "alerts": ["LLM output was not valid JSON"]
#             }
# 
#         except Exception as e:
#             logger.error(f"[LiveMirror] AI analysis failed for session {self.session_id}: {e}")
#             return {
#                 "summary": "Analysis error",
#                 "entities": [],
#                 "keywords_found": [],
#                 "risk_score": 0,
#                 "alerts": [f"Error during analysis: {str(e)}"]
#             }
# 
#     async def get_snapshot(self) -> Dict:
#         """Get current snapshot + AI analysis"""
#         try:
#             if not self.page:
#                 return {"error": "No active page"}
# 
#             snapshot = await self._capture_and_save_snapshot()
# 
#             # Perform AI content analysis
#             analysis = await self._analyze_content(snapshot.text)
# 
#             return {
#                 "success": True,
#                 "snapshot_id": snapshot.id,
#                 "timestamp": snapshot.timestamp.isoformat(),
#                 "html": snapshot.html,
#                 "text": snapshot.text,  # can be removed later to save bandwidth
#                 "screenshot": snapshot.screenshot_base64,
#                 "current_url": snapshot.current_url,
#                 "title": snapshot.title,
#                 "analysis": analysis
#             }
#         except Exception as e:
#             logger.error(f"[LiveMirror] Snapshot failed for {self.session_id}: {e}")
#             return {"error": str(e)}
# 
#     async def start(self, javascript_enabled: bool = False):
#         """
#         Initialize the browser session and capture the initial snapshot
#         """
#         try:
#             pw = await async_playwright().start()
#             self.browser = await pw.chromium.launch(
#                 headless=True,
#                 proxy={"server": f"socks5://{self.tor_socks}"},
#                 args=["--no-sandbox", "--disable-dev-shm-usage"]
#             )
#             self.context = await self.browser.new_context(
#                 viewport={"width": 1280, "height": 900},
#                 java_script_enabled=javascript_enabled
#             )
#             self.page = await self.context.new_page()
# 
#             # Navigate to target URL
#             await self.page.goto(self.target_url, wait_until="domcontentloaded", timeout=90000)
#             self.page_views += 1
# 
#             # Capture and save initial snapshot
#             await self._capture_and_save_snapshot()
# 
#             self.last_activity = datetime.now(timezone.utc)
#             
#             logger.info(f"[LiveMirror] Session {self.session_id} started for {self.target_url}")
#             return True
#         except Exception as e:
#             logger.error(f"[LiveMirror] Failed to start session {self.session_id}: {e}")
#             # Optional: Clean up on failure
#             await self.close()
#             return False
# 
#     async def navigate(self, url: str) -> bool:
#         try:
#             if not self.page:
#                 return False
# 
#             await self.page.goto(url, wait_until="domcontentloaded", timeout=90000)
#             self.page_views += 1
# 
#             await self._capture_and_save_snapshot()
# 
#             logger.info(f"[LiveMirror] Session {self.session_id} navigated to {url}")
#             return True
#         except Exception as e:
#             logger.error(f"[LiveMirror] Navigation failed for {self.session_id}: {e}")
#             return False
# 
#     async def close(self):
#         try:
#             if self.context:
#                 await self.context.close()
#             if self.browser:
#                 await self.browser.close()
#             self.is_active = False
#             logger.info(f"[LiveMirror] Session {self.session_id} closed")
#         except Exception as e:
#             logger.error(f"[LiveMirror] Error closing session {self.session_id}: {e}")
# 
#     def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Snapshot]:
#         for snap in self.snapshots:
#             if snap.id == snapshot_id:
#                 return snap
#         return None
# 
# 
# class LiveMirrorManager:
#     """Manages multiple live mirror sessions"""
# 
#     def __init__(self, tor_socks: str = "127.0.0.1:9050", session_timeout_minutes: int = 10):
#         self.tor_socks = tor_socks
#         self.session_timeout_minutes = session_timeout_minutes
#         self.sessions: Dict[str, LiveMirrorSession] = {}
#         self._cleanup_task = None
# 
#     async def create_session(
#         self,
#         user_id: str,
#         target_url: str,
#         javascript_enabled: bool = False
#     ) -> Optional[str]:
#         try:
#             session_id = str(uuid.uuid4())
# 
#             session = LiveMirrorSession(session_id, user_id, target_url, self.tor_socks)
#             success = await session.start(javascript_enabled)
# 
#             if not success:
#                 return None
# 
#             self.sessions[session_id] = session
#             logger.info(f"[LiveMirror] Created session {session_id} for user {user_id}")
# 
#             return session_id
#         except Exception as e:
#             logger.error(f"[LiveMirror] Failed to create session: {e}")
#             return None
# 
#     def get_session(self, session_id: str) -> Optional[LiveMirrorSession]:
#         return self.sessions.get(session_id)
# 
#     async def close_session(self, session_id: str):
#         session = self.sessions.get(session_id)
#         if session:
#             await session.close()
#             del self.sessions[session_id]
#             logger.info(f"[LiveMirror] Removed session {session_id}")
# 
#     async def cleanup_expired_sessions(self):
#         now = datetime.now(timezone.utc)
#         expired = []
# 
#         for session_id, session in self.sessions.items():
#             time_since_activity = (now - session.last_activity).total_seconds() / 60
#             if time_since_activity > self.session_timeout_minutes:
#                 expired.append(session_id)
# 
#         for session_id in expired:
#             logger.info(f"[LiveMirror] Expiring inactive session {session_id}")
#             await self.close_session(session_id)
# 
#     async def start_cleanup_task(self):
#         while True:
#             try:
#                 await asyncio.sleep(60)  # Check every minute
#                 await self.cleanup_expired_sessions()
#             except Exception as e:
#                 logger.error(f"[LiveMirror] Cleanup task error: {e}")
# 
#     async def shutdown(self):
#         for session_id in list(self.sessions.keys()):
#             await self.close_session(session_id)
#         logger.info("[LiveMirror] Manager shutdown complete")
# 
# 
# async def execute_action(self, action: dict) -> bool:
#     """
#     Execute a user interaction (click, type, scroll, etc.)
#     action example: {"type": "click", "selector": "a[href='/login']"}
#     """
#     if not self.page:
#         return False
# 
#     try:
#         action_type = action.get("type")
# 
#         if action_type == "click":
#             selector = action.get("selector")
#             if selector:
#                 await self.page.click(selector, timeout=10000)
#                 logger.info(f"[LiveMirror] Clicked {selector} in session {self.session_id}")
#                 return True
# 
#         elif action_type == "type":
#             selector = action.get("selector")
#             text = action.get("text")
#             if selector and text is not None:
#                 await self.page.fill(selector, text)
#                 logger.info(f"[LiveMirror] Typed '{text}' into {selector}")
#                 return True
# 
#         elif action_type == "press_key":
#             key = action.get("key")
#             if key:
#                 await self.page.keyboard.press(key)
#                 logger.info(f"[LiveMirror] Pressed key {key}")
#                 return True
# 
#         elif action_type == "scroll":
#             x = action.get("x", 0)
#             y = action.get("y", 300)
#             await self.page.evaluate(f"window.scrollBy({x}, {y})")
#             logger.info(f"[LiveMirror] Scrolled by {x},{y}")
#             return True
# 
#         elif action_type == "submit":
#             selector = action.get("selector") or "form"
#             await self.page.evaluate(f"document.querySelector('{selector}').submit()")
#             logger.info(f"[LiveMirror] Submitted form {selector}")
#             return True
# 
#         else:
#             logger.warning(f"[LiveMirror] Unknown action type: {action_type}")
#             return False
# 
#     except Exception as e:
#         logger.error(f"[LiveMirror] Action failed in session {self.session_id}: {e}")
#         return False
# 
# 
# 
#         
# 
#         
# 
#    
"""
Live Mirror Manager - Manages active browser sessions for live mirroring
with history, diff & AI-powered content analysis
"""

import asyncio
import logging
import uuid
import json
import base64
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any

from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

import ollama

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """Represents a single captured state of the page"""
    id: int
    timestamp: datetime
    html: str
    text: str
    screenshot_base64: str
    current_url: str
    title: str


class LiveMirrorSession:
    """Represents an active live mirror session with history & AI analysis"""

    def __init__(self, session_id: str, target_url: str, tor_socks: str):
        self.session_id = session_id
        self.target_url = target_url
        self.tor_socks = tor_socks
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_active = True
        self.last_activity = datetime.now(timezone.utc)
        self.page_views = 0
        self.screenshots_taken = 0

        self.snapshots: List[Snapshot] = []
        self._next_snapshot_id: int = 1

    async def _capture_and_save_snapshot(self) -> Snapshot:
        """Captures current page state with retry logic for unstable navigation"""
        if not self.page:
            raise RuntimeError("No active page")

        html = ""
        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                # Wait for network to settle
                await self.page.wait_for_load_state("networkidle", timeout=20000)
                html = await self.page.content()
                if len(html) > 500:  # basic sanity check
                    break
            except (PlaywrightTimeoutError, Exception) as e:
                attempts += 1
                logger.debug(f"[Snapshot retry {attempts}/{max_attempts}] for {self.session_id}: {e}")
                if attempts == max_attempts:
                    logger.warning(f"[LiveMirror] Failed to stabilize page content after {max_attempts} attempts")
                    html = "<html><body>Failed to capture stable content</body></html>"
                await asyncio.sleep(2)

        try:
            text = await self.page.evaluate("() => document.body?.innerText || ''")
            screenshot_bytes = await self.page.screenshot(type="png", full_page=True, timeout=30000)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"[LiveMirror] Partial snapshot failure in {self.session_id}: {e}")
            text = ""
            screenshot_base64 = ""

        snapshot = Snapshot(
            id=self._next_snapshot_id,
            timestamp=datetime.now(timezone.utc),
            html=html,
            text=text,
            screenshot_base64=screenshot_base64,
            current_url=self.page.url,
            title=await self.page.title() or "Untitled"
        )

        self.snapshots.append(snapshot)
        self._next_snapshot_id += 1
        self.screenshots_taken += 1
        self.last_activity = datetime.now(timezone.utc)

        return snapshot

    async def _analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze page text using local LLM (Ollama + Llama 3.1)"""
        if not text.strip():
            return {
                "summary": "No readable text content on this page",
                "entities": [],
                "keywords_found": [],
                "risk_score": 0,
                "alerts": []
            }

        prompt = f"""
You are a dark web threat intelligence analyst.
Analyze the following page content from a .onion site:

{text[:12000]}

Tasks:
1. Write a concise summary (2-4 sentences) of what the page is about.
2. Extract key entities: people names, organizations, companies, cryptocurrencies (BTC/XMR addresses), emails, domains, phone numbers.
3. Detect these suspicious keywords/phrases (only return matches):
   - leak, dump, database, breach, credentials, password, credit card
   - ransomware, malware, exploit, 0day, cve, hacking, ddos
   - buy, sell, vendor, shop, market, escrow, carding
   - hitman, assassin, murder, kill, weapon
   - child, cp, porn, underage, lolita
   - bitcoin, monero, xmr, wallet, crypto
4. Calculate a risk score (0-100):
   - 80-100: Clear illegal activity (markets, leaks, threats, CSAM)
   - 50-79: Suspicious (hacking forums, carding mentions)
   - 20-49: Potentially risky (dark web forums, privacy tools)
   - 0-19: Low risk (news, blogs, normal discussion)

CRITICAL RULES:
- Output **ONLY** valid JSON. Nothing else.
- No explanations, no markdown, no code blocks, no ```json tags.
- The JSON must be directly parseable with json.loads().
- Use this exact structure:

{{
  "summary": "short summary here",
  "entities": ["entity1", "entity2"],
  "keywords_found": ["keyword1", "keyword2"],
  "risk_score": 85,
  "alerts": ["High risk: leaked credentials detected"]
}}
"""

        try:
            response = await asyncio.to_thread(
                ollama.generate,
                model="llama3.1:8b",
                prompt=prompt,
                options={"temperature": 0.0, "num_predict": 1024}
            )

            raw = response['response'].strip()
            start = raw.find('{')
            end = raw.rfind('}') + 1

            if start != -1 and end > start:
                json_str = raw[start:end]
                analysis = json.loads(json_str)

                defaults = {
                    "summary": "",
                    "entities": [],
                    "keywords_found": [],
                    "risk_score": 0,
                    "alerts": []
                }
                for k, v in defaults.items():
                    analysis.setdefault(k, v)
                    if k == "risk_score" and not isinstance(analysis[k], (int, float)):
                        analysis[k] = 0

                return analysis

            logger.warning(f"[LiveMirror] No valid JSON in Ollama response for {self.session_id}")
            return {
                "summary": "Analysis failed - invalid format",
                "entities": [],
                "keywords_found": [],
                "risk_score": 0,
                "alerts": ["Invalid LLM output"]
            }

        except Exception as e:
            logger.error(f"[LiveMirror] AI analysis failed for {self.session_id}: {e}")
            return {
                "summary": "Analysis error",
                "entities": [],
                "keywords_found": [],
                "risk_score": 0,
                "alerts": [f"Error: {str(e)}"]
            }

    async def get_snapshot(self) -> Dict:
        try:
            if not self.page:
                return {"error": "No active page"}

            snapshot = await self._capture_and_save_snapshot()
            analysis = await self._analyze_content(snapshot.text)

            return {
                "success": True,
                "snapshot_id": snapshot.id,
                "timestamp": snapshot.timestamp.isoformat(),
                "html": snapshot.html,
                "text": snapshot.text,
                "screenshot": snapshot.screenshot_base64,
                "current_url": snapshot.current_url,
                "title": snapshot.title,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"[LiveMirror] Snapshot failed for {self.session_id}: {e}")
            return {"error": str(e)}

    async def start(self, javascript_enabled: bool = False):
        """Initialize browser session with robust navigation waiting"""
        try:
            pw = await async_playwright().start()
            self.browser = await pw.chromium.launch(
                headless=True,
                proxy={"server": f"socks5://{self.tor_socks}"},
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 900},
                java_script_enabled=javascript_enabled,
                ignore_https_errors=True,
                bypass_csp=True
            )
            self.page = await self.context.new_page()

            # Navigate with stronger wait conditions
            await self.page.goto(
                self.target_url,
                wait_until="networkidle",
                timeout=120000
            )

            # Extra safety for slow/redirect-heavy .onion sites
            try:
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logger.debug(f"[LiveMirror] networkidle timeout after goto - continuing anyway")

            # Final safety delay (often needed on Tor)
            await asyncio.sleep(4)

            self.page_views += 1
            await self._capture_and_save_snapshot()

            self.last_activity = datetime.now(timezone.utc)
            logger.info(f"[LiveMirror] Session {self.session_id} started for {self.target_url}")
            return True

        except Exception as e:
            logger.error(f"[LiveMirror] Failed to start session {self.session_id}: {e}")
            await self.close()
            return False

    async def navigate(self, url: str) -> bool:
        try:
            if not self.page:
                return False

            await self.page.goto(url, wait_until="networkidle", timeout=90000)
            await asyncio.sleep(3)  # safety delay after navigation

            self.page_views += 1
            await self._capture_and_save_snapshot()

            logger.info(f"[LiveMirror] Session {self.session_id} navigated to {url}")
            return True
        except Exception as e:
            logger.error(f"[LiveMirror] Navigation failed for {self.session_id}: {e}")
            return False

    async def close(self):
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            self.is_active = False
            logger.info(f"[LiveMirror] Session {self.session_id} closed")
        except Exception as e:
            logger.error(f"[LiveMirror] Error closing session {self.session_id}: {e}")

    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Snapshot]:
        for snap in self.snapshots:
            if snap.id == snapshot_id:
                return snap
        return None


class LiveMirrorManager:
    """Manages multiple live mirror sessions"""

    def __init__(self, tor_socks: str = "127.0.0.1:9050", session_timeout_minutes: int = 10):
        self.tor_socks = tor_socks
        self.session_timeout_minutes = session_timeout_minutes
        self.sessions: Dict[str, LiveMirrorSession] = {}
        self._cleanup_task = None

    async def create_session(
        self,
        target_url: str,
        javascript_enabled: bool = False
    ) -> Optional[str]:
        try:
            session_id = str(uuid.uuid4())
            session = LiveMirrorSession(session_id, target_url, self.tor_socks)
            success = await session.start(javascript_enabled)

            if not success:
                return None

            self.sessions[session_id] = session
            logger.info(f"[LiveMirror] Created session {session_id} for {target_url}")
            return session_id
        except Exception as e:
            logger.error(f"[LiveMirror] Failed to create session: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[LiveMirrorSession]:
        return self.sessions.get(session_id)

    async def close_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            await session.close()
            del self.sessions[session_id]
            logger.info(f"[LiveMirror] Removed session {session_id}")

    async def cleanup_expired_sessions(self):
        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, s in self.sessions.items()
            if (now - s.last_activity).total_seconds() / 60 > self.session_timeout_minutes
        ]

        for sid in expired:
            logger.info(f"[LiveMirror] Expiring inactive session {sid}")
            await self.close_session(sid)

    async def start_cleanup_task(self):
        while True:
            try:
                await asyncio.sleep(60)
                await self.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"[LiveMirror] Cleanup task error: {e}")

    async def shutdown(self):
        for sid in list(self.sessions.keys()):
            await self.close_session(sid)
        logger.info("[LiveMirror] Manager shutdown complete")


# Note: execute_action seems to be defined outside any class.
# If this is meant to be a method of LiveMirrorSession, move it inside:
# async def execute_action(self, action: dict) -> bool:
#     ...