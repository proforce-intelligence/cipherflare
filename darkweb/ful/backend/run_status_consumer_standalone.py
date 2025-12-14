#!/usr/bin/env python3
"""
Standalone Status Consumer Runner

Run this if you want to run the status consumer separately from the API.
Normally, the status consumer runs automatically as a background task in the API.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.status_consumer import run_status_consumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 60)
    print("Status Consumer - Standalone Mode")
    print("=" * 60)
    print("\nNOTE: The status consumer runs automatically within the API.")
    print("Only run this standalone if you're debugging or testing.\n")
    
    try:
        asyncio.run(run_status_consumer())
    except KeyboardInterrupt:
        print("\n[✓] Status consumer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        sys.exit(1)
