# create_tables.py
import asyncio
import os
import sys

# Add the current directory to sys.path so we can find 'app'
sys.path.append(os.getcwd())

from app.database.database import init_db

async def main():
    print("Initializing fresh database...")
    await init_db()
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
