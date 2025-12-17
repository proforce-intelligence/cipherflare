from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
import asyncio
from typing import Optional
from pathlib import Path

from app.api.routes import search, monitor, files
from app.api.routes.monitoring_jobs import router as monitoring_jobs_router, set_scheduler
from app.api.routes.settings import router as settings_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.stats import router as stats_router
from app.api.routes.live_mirror import router as live_mirror_router
from app.database.database import init_db
from app.services.scheduler import MonitoringScheduler
from app.services.status_consumer import StatusConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dark Web Threat Intelligence API",
    description="Production-grade dark web monitoring and searching with LLM analysis and PGP verification",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:4000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4000",
        "http://192.168.1.175:4000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE", "./dark_web_results"))
if OUTPUT_BASE.exists():
    app.mount("/files", StaticFiles(directory=str(OUTPUT_BASE)), name="files")
    logger.info(f"[✓] Mounted /files directory: {OUTPUT_BASE}")
else:
    logger.warning(f"[!] Output directory not found: {OUTPUT_BASE}")

app.include_router(search.router)
app.include_router(monitor.router)
app.include_router(monitoring_jobs_router)
app.include_router(settings_router)
app.include_router(jobs_router)
app.include_router(alerts_router)
app.include_router(stats_router)
app.include_router(live_mirror_router)

_scheduler: Optional[MonitoringScheduler] = None
_status_consumer: Optional[StatusConsumer] = None

@app.on_event("startup")
async def startup():
    """Initialize database and scheduler on startup"""
    global _scheduler
    global _status_consumer
    
    try:
        from scripts.migrate_database import migrate_database
        await migrate_database()
        logger.info("[✓] Database migration completed")
    except Exception as e:
        logger.warning(f"[!] Migration warning: {e}")
    
    try:
        await init_db()
        logger.info("[✓] Database initialized")
    except Exception as e:
        logger.error(f"[!] Database initialization failed: {e}")
    
    try:
        _scheduler = MonitoringScheduler()
        await _scheduler.initialize()
        
        set_scheduler(_scheduler)
        
        asyncio.create_task(_scheduler.start())
        logger.info("[✓] Monitoring scheduler initialized and started")
    except Exception as e:
        logger.warning(f"[!] Scheduler initialization warning (may be normal if broker unavailable): {e}")
    
    try:
        _status_consumer = StatusConsumer()
        asyncio.create_task(_status_consumer.start())
        logger.info("[✓] Status consumer started - listening for job updates")
    except Exception as e:
        logger.warning(f"[!] Status consumer initialization warning: {e}")
    
    from app.api.routes.live_mirror import get_live_mirror_manager
    try:
        manager = get_live_mirror_manager()
        asyncio.create_task(manager.start_cleanup_task())
        logger.info("[✓] Live mirror manager initialized")
    except Exception as e:
        logger.warning(f"[!] Live mirror manager warning: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    global _scheduler
    global _status_consumer
    
    if _scheduler:
        try:
            await _scheduler.shutdown()
            logger.info("[✓] Scheduler shutdown complete")
        except Exception as e:
            logger.error(f"[!] Scheduler shutdown error: {e}")
    
    if _status_consumer:
        try:
            await _status_consumer.stop()
            logger.info("[✓] Status consumer shutdown complete")
        except Exception as e:
            logger.error(f"[!] Status consumer shutdown error: {e}")
    
    from app.api.routes.live_mirror import get_live_mirror_manager
    try:
        manager = get_live_mirror_manager()
        await manager.shutdown()
        logger.info("[✓] Live mirror manager shutdown complete")
    except Exception as e:
        logger.error(f"[!] Live mirror manager shutdown error: {e}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "dark-web-api"}

@app.get("/")
async def root():
    """API root"""
    return {
        "name": "Dark Web Threat Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": {
            "search": "Dark web content search with hybrid indexing",
            "monitoring": "Continuous .onion site monitoring",
            "alerts": "Real-time threat alerts",
            "llm_analysis": "AI-powered threat summaries with Google Gemini (default)",
            "pgp_verification": "Legitimacy verification for .onion sites",
            "provider_switching": "Switch between LLM providers (OpenAI, Anthropic, Google, etc.)",
            "live_mirror": "Real-time .onion site mirroring via WebSocket"
        }
    }
