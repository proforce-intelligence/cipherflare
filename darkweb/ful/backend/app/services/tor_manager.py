import asyncio
import logging
import os
from typing import Tuple
import socket

logger = logging.getLogger(__name__)

try:
    from stem import Signal
    from stem.control import Controller
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False
    logger.warning("[!] stem library not installed - Tor rotation disabled")

class TorManager:
    """Manage Tor proxy connection and identity rotation"""
    
    def __init__(self, socks_addr: str = "127.0.0.1:9050", control_addr: str = None):
        self.socks_addr = socks_addr
        self.socks_host, self.socks_port = socks_addr.split(":")
        self.socks_port = int(self.socks_port)
        
        # Control port from env or derived from SOCKS port
        if control_addr:
            self.control_host, self.control_port = control_addr.split(":")
            self.control_port = int(self.control_port)
        else:
            self.control_host = os.getenv("TOR_CONTROL_HOST", "127.0.0.1")
            self.control_port = int(os.getenv("TOR_CONTROL_PORT", "9051"))
        
        self.control_password = os.getenv("TOR_CONTROL_PASS", "")
        self.stem_available = STEM_AVAILABLE
    
    def check_tor_connectivity(self) -> bool:
        """Test if Tor SOCKS proxy is reachable"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.socks_host, self.socks_port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"[!] Tor connectivity check failed: {e}")
            return False
    
    async def rotate_identity(self) -> Tuple[bool, str]:
        """
        Rotate Tor identity via NEWNYM signal
        Returns: (success: bool, message: str)
        """
        if not self.stem_available:
            return False, "stem library not available"
        
        if not self.check_tor_connectivity():
            return False, f"Tor SOCKS proxy unreachable at {self.socks_addr}"
        
        try:
            with Controller.from_port(
                address=self.control_host,
                port=self.control_port
            ) as controller:
                if self.control_password:
                    controller.authenticate(password=self.control_password)
                else:
                    # Try passwordless auth first (for CookieAuthentication)
                    try:
                        controller.authenticate()
                    except Exception as auth_error:
                        logger.warning(f"[!] Passwordless auth failed: {auth_error}")
                        logger.warning("[!] Set TOR_CONTROL_PASS or enable CookieAuthentication in torrc")
                        return False, "Cannot authenticate with Tor control port"
                
                controller.signal(Signal.NEWNYM)
                
                # Wait for signal to be processed
                await asyncio.sleep(2)
                
                return True, f"Tor identity rotated via {self.control_host}:{self.control_port}"
        
        except Exception as e:
            logger.error(f"[!] Tor rotation failed: {e}")
            return False, f"Rotation failed: {str(e)}"
    
    def get_socks_proxy_dict(self) -> dict:
        """Get proxy dict for requests library"""
        socks5_proxy = f"socks5h://{self.socks_addr}"
        return {
            "http": socks5_proxy,
            "https": socks5_proxy
        }
    
    def get_playwright_proxy(self) -> dict:
        """Get proxy config for Playwright"""
        return {
            "server": f"socks5://{self.socks_addr}"
        }
