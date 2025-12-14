#!/usr/bin/env python3
"""
Initialize Tor configuration - sets up control port authentication.
This is required for Tor identity rotation to work.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_tor_env():
    """
    Check Tor configuration and provide setup instructions
    """
    logger.info("[*] Checking Tor configuration...")
    
    # Check environment variables
    tor_control_pass = os.getenv("TOR_CONTROL_PASS", "")
    tor_control_host = os.getenv("TOR_CONTROL_HOST", "127.0.0.1")
    tor_control_port = os.getenv("TOR_CONTROL_PORT", "9051")
    tor_socks_addr = os.getenv("TOR_SOCKS_ADDR", "127.0.0.1:9050")
    
    logger.info(f"[*] Tor SOCKS: {tor_socks_addr}")
    logger.info(f"[*] Tor Control: {tor_control_host}:{tor_control_port}")
    
    if not tor_control_pass:
        logger.warning("[!] TOR_CONTROL_PASS environment variable not set")
        logger.info("[*] For passwordless auth, ensure your torrc has: CookieAuthentication 1")
        logger.info("[*] Or set TOR_CONTROL_PASS to your control port password")
    else:
        logger.info("[✓] TOR_CONTROL_PASS is set")
    
    return True

if __name__ == "__main__":
    setup_tor_env()
