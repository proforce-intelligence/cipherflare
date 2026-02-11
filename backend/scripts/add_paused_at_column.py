
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Determine the path to the database file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/dark_web.db"

async def add_paused_at_column():
    print(f"Attempting to connect to database: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.connect() as conn:
        # Check if the column already exists
        # This is a SQLite-specific way to get table info
        result = await conn.execute(text("PRAGMA table_info(jobs);"))
        columns = [row[1] for row in result] # column name is at index 1

        if "paused_at" not in columns:
            print("Column 'paused_at' not found in 'jobs' table. Adding it now...")
            try:
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN paused_at DATETIME NULL;"))
                await conn.commit()
                print("Column 'paused_at' added successfully to 'jobs' table.")
            except Exception as e:
                print(f"Error adding column: {e}")
                await conn.rollback()
        else:
            print("Column 'paused_at' already exists in 'jobs' table. No action needed.")
    
    await engine.dispose()
    print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(add_paused_at_column())
