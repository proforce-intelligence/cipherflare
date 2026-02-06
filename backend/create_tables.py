# create_tables.py
import asyncio
from app.database.database import engine, Base
from app.models.report import Report   # ← make sure this import works

async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully (including 'reports')!")

if __name__ == "__main__":
    asyncio.run(create_all_tables())
