#!/usr/bin/env python3
"""
Initialize Playwright browsers - must be run once before starting workers.
This installs Chromium, Firefox, and WebKit browsers.
"""
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_playwright_browsers():
    """Install Playwright browsers"""
    try:
        logger.info("[*] Installing Playwright browsers (this may take 2-3 minutes)...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install"],
            check=True,
            capture_output=False
        )
        logger.info("[✓] Playwright browsers installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[!] Failed to install Playwright browsers: {e}")
        return False
    except Exception as e:
        logger.error(f"[!] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = install_playwright_browsers()
    sys.exit(0 if success else 1)
