# truncate_db.py
import asyncio
import os
import sys
from sqlalchemy import text

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.database.database import engine, init_db

async def truncate():
    print("Connecting to database to truncate all tables...")
    async with engine.begin() as conn:
        # Get all table names
        if "sqlite" in str(engine.url):
            # SQLite specific truncation (delete from tables)
            tables = ["users", "jobs", "alerts", "monitoring_results", "monitoring_jobs", "reports"]
            for table in tables:
                try:
                    await conn.execute(text(f"DELETE FROM {table}"))
                    print(f"Truncated {table}")
                except Exception as e:
                    print(f"Skipping {table}: {e}")
        else:
            # Generic approach for other DBs if needed
            pass
    print("Database truncation complete.")

if __name__ == "__main__":
    asyncio.run(truncate())
