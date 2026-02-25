from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import os
import logging
import sys

logger = logging.getLogger(__name__)

# Check if aiosqlite is available
try:
    import aiosqlite
    logger.info(f"[✓] aiosqlite is available (version {aiosqlite.__version__})")
except ImportError:
    logger.error("[!] aiosqlite is not installed. Installing it...")
    os.system(f"{sys.executable} -m pip install aiosqlite")
    try:
        import aiosqlite
        logger.info(f"[✓] aiosqlite installed (version {aiosqlite.__version__})")
    except ImportError:
        logger.error("[!] Failed to install aiosqlite. Cannot proceed with async SQLite.")
        raise RuntimeError("aiosqlite is required for async SQLite support")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./dark_web.db"
)

# Ensure we're using the async driver, not the synchronous one
if DATABASE_URL.startswith("sqlite://"):
    logger.warning(f"[!] DATABASE_URL uses synchronous driver: {DATABASE_URL}")
    # Replace sqlite:// with sqlite+aiosqlite://
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
    logger.info(f"[✓] Converted to async driver: {DATABASE_URL}")
elif not DATABASE_URL.startswith("sqlite+aiosqlite://"):
    logger.warning(f"[!] Unexpected DATABASE_URL format: {DATABASE_URL}")

logger.info(f"[✓] Using DATABASE_URL: {DATABASE_URL}")

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False") == "True",
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"timeout": 30, "check_same_thread": False}
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
    from app.models.monitoring_result import Base as MonitoringResultBase
    from app.models.monitoring_job import Base as MonitoringJobBase
    from app.models.report import Base as ReportBase
    from app.models.wallet import Base as WalletBase
    
    async with engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(JobBase.metadata.create_all)
        await conn.run_sync(AlertBase.metadata.create_all)
        await conn.run_sync(MonitoringResultBase.metadata.create_all)
        await conn.run_sync(MonitoringJobBase.metadata.create_all)
        await conn.run_sync(ReportBase.metadata.create_all)
        await conn.run_sync(WalletBase.metadata.create_all)

@asynccontextmanager
async def get_db_context():
    """Context manager for standalone scripts"""
    async with AsyncSessionLocal() as session:
        yield session
