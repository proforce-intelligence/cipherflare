"""
Database migration script to add missing columns
"""
import asyncio
import aiosqlite
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_database():
    """Add missing columns to existing database"""
    db_path = Path("./dark_web.db")
    
    if not db_path.exists():
        logger.info("[*] No database found, will be created on startup")
        return
    
    async with aiosqlite.connect(str(db_path)) as db:
        try:
            # Check if deactivated_at column exists
            cursor = await db.execute("PRAGMA table_info(alerts)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if "deactivated_at" not in column_names:
                logger.info("[*] Adding deactivated_at column to alerts table...")
                await db.execute(
                    "ALTER TABLE alerts ADD COLUMN deactivated_at DATETIME"
                )
                await db.commit()
                logger.info("[✓] Added deactivated_at column")
            else:
                logger.info("[✓] deactivated_at column already exists")
            
            logger.info("[✓] Database migration completed")
            
        except Exception as e:
            logger.error(f"[!] Migration failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate_database())
