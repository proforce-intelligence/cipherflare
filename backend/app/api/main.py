from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import asyncio

from app.api.routes import search, monitor
from app.api.routes.monitoring_jobs import router as monitoring_jobs_router, set_scheduler
from app.api.routes.settings import router as settings_router
from app.database.database import init_db
from app.services.scheduler import MonitoringScheduler

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
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(monitor.router)
app.include_router(monitoring_jobs_router)
app.include_router(settings_router)

_scheduler: MonitoringScheduler = None

@app.on_event("startup")
async def startup():
    """Initialize database and scheduler on startup"""
    global _scheduler
    
    try:
        await init_db()
        logger.info("[✓] Database initialized")
    except Exception as e:
        logger.error(f"[!] Database initialization failed: {e}")
    
    try:
        _scheduler = MonitoringScheduler()
        await _scheduler.initialize()
        
        # Set scheduler in monitoring_jobs router
        set_scheduler(_scheduler)
        
        # Start scheduler in background task
        asyncio.create_task(_scheduler.start())
        logger.info("[✓] Monitoring scheduler initialized and started")
    except Exception as e:
        logger.warning(f"[!] Scheduler initialization warning (may be normal if broker unavailable): {e}")

@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    global _scheduler
    
    if _scheduler:
        try:
            await _scheduler.shutdown()
            logger.info("[✓] Scheduler shutdown complete")
        except Exception as e:
            logger.error(f"[!] Scheduler shutdown error: {e}")

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
            "provider_switching": "Switch between LLM providers (OpenAI, Anthropic, Google, etc.)"
        }
    }
