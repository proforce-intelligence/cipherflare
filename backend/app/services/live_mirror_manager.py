"""
Live Mirror Manager - Manages active browser sessions for live mirroring
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class LiveMirrorSession:
    """Represents an active live mirror session"""
    
    def __init__(self, session_id: str, user_id: str, target_url: str, tor_socks: str):
        self.session_id = session_id
        self.user_id = user_id
        self.target_url = target_url
        self.tor_socks = tor_socks
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_active = True
        self.last_activity = datetime.now(timezone.utc)
        self.page_views = 0
        self.screenshots_taken = 0
    
    async def start(self, javascript_enabled: bool = False):
        """Initialize browser session"""
        try:
            pw = await async_playwright().start()
            self.browser = await pw.chromium.launch(
                headless=True,
                proxy={"server": f"socks5://{self.tor_socks}"},
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 900},
                java_script_enabled=javascript_enabled
            )
            self.page = await self.context.new_page()
            
            # Navigate to target URL
            await self.page.goto(self.target_url, wait_until="domcontentloaded", timeout=90000)
            self.page_views += 1
            self.last_activity = datetime.now(timezone.utc)
            
            logger.info(f"[LiveMirror] Session {self.session_id} started for {self.target_url}")
            return True
        except Exception as e:
            logger.error(f"[LiveMirror] Failed to start session {self.session_id}: {e}")
            return False
    
    async def get_snapshot(self) -> Dict:
        """Get current page snapshot (HTML + screenshot)"""
        try:
            if not self.page:
                return {"error": "No active page"}
            
            # Get HTML content
            html = await self.page.content()
            
            # Get visible text
            text = await self.page.evaluate("() => document.body ? document.body.innerText : ''")
            
            # Take screenshot
            screenshot_bytes = await self.page.screenshot(type="png", full_page=False)
            import base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Get current URL
            current_url = self.page.url
            
            # Get page title
            title = await self.page.title()
            
            self.screenshots_taken += 1
            self.last_activity = datetime.now(timezone.utc)
            
            return {
                "success": True,
                "html": html,
                "text": text,
                "screenshot": screenshot_base64,
                "current_url": current_url,
                "title": title,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"[LiveMirror] Snapshot failed for {self.session_id}: {e}")
            return {"error": str(e)}
    
    async def navigate(self, url: str) -> bool:
        """Navigate to a new URL"""
        try:
            if not self.page:
                return False
            
            await self.page.goto(url, wait_until="domcontentloaded", timeout=90000)
            self.page_views += 1
            self.last_activity = datetime.now(timezone.utc)
            
            logger.info(f"[LiveMirror] Session {self.session_id} navigated to {url}")
            return True
        except Exception as e:
            logger.error(f"[LiveMirror] Navigation failed for {self.session_id}: {e}")
            return False
    
    async def close(self):
        """Close browser session"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            self.is_active = False
            logger.info(f"[LiveMirror] Session {self.session_id} closed")
        except Exception as e:
            logger.error(f"[LiveMirror] Error closing session {self.session_id}: {e}")


class LiveMirrorManager:
    """Manages multiple live mirror sessions"""
    
    def __init__(self, tor_socks: str = "127.0.0.1:9050", session_timeout_minutes: int = 10):
        self.tor_socks = tor_socks
        self.session_timeout_minutes = session_timeout_minutes
        self.sessions: Dict[str, LiveMirrorSession] = {}
        self._cleanup_task = None
    
    async def create_session(
        self, 
        user_id: str, 
        target_url: str, 
        javascript_enabled: bool = False
    ) -> Optional[str]:
        """Create a new live mirror session"""
        try:
            session_id = str(uuid.uuid4())
            
            session = LiveMirrorSession(session_id, user_id, target_url, self.tor_socks)
            success = await session.start(javascript_enabled)
            
            if not success:
                return None
            
            self.sessions[session_id] = session
            logger.info(f"[LiveMirror] Created session {session_id} for user {user_id}")
            
            return session_id
        except Exception as e:
            logger.error(f"[LiveMirror] Failed to create session: {e}")
            return None
    
    def get_session(self, session_id: str) -> Optional[LiveMirrorSession]:
        """Get an active session by ID"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str):
        """Close and remove a session"""
        session = self.sessions.get(session_id)
        if session:
            await session.close()
            del self.sessions[session_id]
            logger.info(f"[LiveMirror] Removed session {session_id}")
    
    async def cleanup_expired_sessions(self):
        """Remove sessions that have expired"""
        now = datetime.now(timezone.utc)
        expired = []
        
        for session_id, session in self.sessions.items():
            time_since_activity = (now - session.last_activity).total_seconds() / 60
            if time_since_activity > self.session_timeout_minutes:
                expired.append(session_id)
        
        for session_id in expired:
            logger.info(f"[LiveMirror] Expiring inactive session {session_id}")
            await self.close_session(session_id)
    
    async def start_cleanup_task(self):
        """Start background task to cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"[LiveMirror] Cleanup task error: {e}")
    
    async def shutdown(self):
        """Close all sessions"""
        for session_id in list(self.sessions.keys()):
            await self.close_session(session_id)
        logger.info("[LiveMirror] Manager shutdown complete")
