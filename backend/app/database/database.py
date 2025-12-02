from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./dark_web.db"  # Local SQLite for development
)

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False") == "True",
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    """Dependency for FastAPI to get DB session"""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initialize database tables"""
    from app.models.user import Base as UserBase
    from app.models.job import Base as JobBase
    from app.models.alert import Base as AlertBase
    
    async with engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(JobBase.metadata.create_all)
        await conn.run_sync(AlertBase.metadata.create_all)

@asynccontextmanager
async def get_db_context():
    """Context manager for standalone scripts"""
    async with AsyncSessionLocal() as session:
        yield session
