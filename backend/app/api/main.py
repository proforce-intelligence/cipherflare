from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordRequestForm
import logging
import os
import asyncio
from typing import Optional
from pathlib import Path
from datetime import timedelta, datetime

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db, init_db
from app.models.user import User, AuditLog, LoginLog
from app.core.security import (
    verify_password,
    create_token,
    get_current_user,
    set_secure_auth_cookies,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
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
    response: Response,                             # Required to set cookies
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    request: Request = None,                        # Optional: for IP logging
):
    """
    Authenticate user, set secure HTTP-only cookies, and return tokens in body.
    PUBLIC endpoint — no authentication required.
    """
    # Safely get client info (fallback to "unknown")
    ip_address = request.client.host if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"

    # Find user
    result = await db.execute(select(User).where(User.username == form.username))
    user: User | None = result.scalar_one_or_none()

    # Verify credentials
    success = user is not None and verify_password(form.password, user.hashed_password)

    # Log attempt (success or failure)
    login_log = LoginLog(
        user_id=user.id if user else None,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
    )
    db.add(login_log)

    if not success:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Authentication successful ────────────────────────────────────────

    # Create tokens
    access_token = create_token(
        subject=str(user.id),
        role=user.role.value,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )

    refresh_token = create_token(
        subject=str(user.id),
        role=user.role.value,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )

    # Set secure HTTP-only cookies BEFORE any commit/return
    set_secure_auth_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_token,
        request=request,
    )

    # Log successful login
    db.add(
        AuditLog(
            user_id=user.id,
            action="login_success",
            details={"ip": ip_address, "user_agent": user_agent},
        )
    )

    # Commit both logs
    await db.commit()

    # Return tokens in body (useful for Swagger, Postman, mobile apps, etc.)
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "status": "ACTIVE" if user.is_active else "INACTIVE",
            "created_at": user.created_at.isoformat() if user.created_at else None,
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
    logger.info("[Startup] Initializing database tables...")
    try:
        await init_db()
        logger.info("[Database] ✓ Tables created / verified successfully")
    except Exception as e:
        logger.error("[Database] Table creation failed", exc_info=True)
        # raise   # ← uncomment in dev to fail fast
    
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
