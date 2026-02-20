from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
import logging
import os
import asyncio
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db, init_db
from app.models.user import User, AuditLog, LoginLog
from app.core.security import (
    verify_password,
    create_token,
    get_current_user,
)

from app.api.routes.auth import auth
from app.api.routes import search, monitor, files
from app.api.routes.monitoring_jobs import router as monitoring_jobs_router, set_scheduler
from app.api.routes.settings import router as settings_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.stats import router as stats_router
from app.api.routes.live_mirror import router as live_mirror_router
from app.api.routes.reporting import router as reporting_router

from app.services.scheduler import MonitoringScheduler
from app.services.status_consumer import StatusConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dark Web Threat Intelligence API",
    description="Production-grade dark web monitoring and searching with LLM analysis and PGP verification",
    version="1.0.0",
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
        "http://192.168.1.222:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mount
OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE", "./dark_web_results"))
if OUTPUT_BASE.exists():
    app.mount("/files", StaticFiles(directory=str(OUTPUT_BASE)), name="files")
    logger.info(f"[✓] Mounted /files directory: {OUTPUT_BASE}")
else:
    logger.warning(f"[!] Output directory not found: {OUTPUT_BASE}")

# ────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS (no authentication required)
# ────────────────────────────────────────────────────────────────


@app.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db), # Keep db dependency for consistency if needed by other parts, but it's unused here
):
    """
    Bypassed login endpoint: always returns dummy tokens.
    """
    # Since authentication is disabled, we bypass actual user verification.
    # Always return a dummy token for any login attempt.
    return {
        "access_token": create_token(subject="dummy_user_id", role="super_admin", token_type="access"),
        "refresh_token": create_token(subject="dummy_user_id", role="super_admin", token_type="refresh"),
        "token_type": "bearer",
        "expires_in": 3600, # 1 hour dummy expiry
        "message": "Login successful (authentication bypassed)",
        "user": {
            "id": "dummy_user_id",
            "username": "dummy_user",
            "role": "super_admin",
            "status": "ACTIVE",
            "created_at": datetime.now().isoformat(),
        }
    }

@app.get("/health", dependencies=[], tags=["public"])
async def health():
    """Health check endpoint – no authentication required"""
    return {"status": "ok", "service": "dark-web-api"}


@app.get("/", dependencies=[], tags=["public"])
async def root():
    """API root – public information"""
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

# ────────────────────────────────────────────────────────────────
# Include routers
# ────────────────────────────────────────────────────────────────




app.include_router(auth)
app.include_router(search.router)
app.include_router(monitor.router)
app.include_router(monitoring_jobs_router)
app.include_router(settings_router)
app.include_router(jobs_router)
app.include_router(alerts_router)
app.include_router(stats_router)
app.include_router(live_mirror_router)
app.include_router(reporting_router)

# ────────────────────────────────────────────────────────────────
# Custom OpenAPI schema
# ────────────────────────────────────────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Enter your JWT access token.\n\n"
                "How to use:\n"
                "1. First login → POST /api/v1/auth/login\n"
                "2. Copy the 'access_token' from the response\n"
                "3. Paste it here in the format: Bearer <your-token>\n\n"
                "This token will be used for all protected endpoints."
            )
        }
    }

    # Global security requirement (but public endpoints override it)
    # openapi_schema["security"] = [{"BearerAuth": []}]
    

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global services
_scheduler: Optional[MonitoringScheduler] = None
_status_consumer: Optional[StatusConsumer] = None

@app.on_event("startup")
async def startup():
    global _scheduler, _status_consumer
    
    # Initialize database
    await init_db()
    logger.info("[✓] Database initialized")
    
    # Start Status Consumer in background
    _status_consumer = StatusConsumer()
    asyncio.create_task(_status_consumer.start())
    logger.info("[✓] Status Consumer started in background")
    
    # Initialize and start Monitoring Scheduler
    _scheduler = MonitoringScheduler()
    await _scheduler.initialize()
    await _scheduler.start()
    
    # Set scheduler in routes
    set_scheduler(_scheduler)
    # Also set in monitor router if needed
    monitor.set_scheduler(_scheduler)
    
    logger.info("[✓] Monitoring Scheduler started")

@app.on_event("shutdown")
async def shutdown():
    if _scheduler:
        await _scheduler.shutdown()
    if _status_consumer:
        await _status_consumer.stop()
    logger.info("[✓] Services shutdown complete")