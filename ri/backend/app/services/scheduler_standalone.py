#!/usr/bin/env python3
"""
Standalone monitoring scheduler service
Run independently from the main API for production deployments
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.scheduler import MonitoringScheduler
from app.database.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run standalone scheduler"""
    try:
        logger.info("[Scheduler] Initializing database...")
        await init_db()
        
        logger.info("[Scheduler] Creating scheduler instance...")
        scheduler = MonitoringScheduler()
        await scheduler.initialize()
        
        logger.info("[Scheduler] Starting scheduler service...")
        await scheduler.start()
        
        logger.info("[Scheduler] Service running. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("[Scheduler] Shutdown signal received")
        if scheduler:
            await scheduler.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"[Scheduler] Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
