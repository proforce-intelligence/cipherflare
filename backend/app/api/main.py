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

from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db, init_db
from app.models.user import User, AuditLog, LoginLog
from app.core.security import (
    verify_password,
    create_token,
    get_current_user,
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
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return access + refresh tokens in response body.
    This endpoint is PUBLIC (no authentication required).
    """
    ip_address = "unknown"      # You can get real IP from middleware or proxy headers if needed
    user_agent = "unknown"      # You can get from headers if needed

    # Find user
    result = await db.execute(select(User).where(User.username == form.username))
    user: User | None = result.scalar_one_or_none()

    # Check credentials
    success = user is not None and verify_password(form.password, user.hashed_password)

    # Log attempt (even failed ones)
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

    # Log successful login
    db.add(
        AuditLog(
            user_id=user.id,
            action="login_success",
            details={"ip": ip_address, "user_agent": user_agent},
        )
    )

    await db.commit()

    # Return tokens + basic user info (Bearer style)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
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




app.include_router(auth,                         dependencies=[Depends(get_current_user)])
app.include_router(search.router,                dependencies=[Depends(get_current_user)])
app.include_router(monitor.router,               dependencies=[Depends(get_current_user)])
app.include_router(monitoring_jobs_router,       dependencies=[Depends(get_current_user)])
app.include_router(settings_router,              dependencies=[Depends(get_current_user)])
app.include_router(jobs_router,                  dependencies=[Depends(get_current_user)])
app.include_router(alerts_router,                dependencies=[Depends(get_current_user)])
app.include_router(stats_router,                 dependencies=[Depends(get_current_user)])
app.include_router(live_mirror_router,           dependencies=[Depends(get_current_user)])
app.include_router(reporting_router,             dependencies=[Depends(get_current_user)])

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

# Global services (unchanged)
_scheduler: Optional[MonitoringScheduler] = None
_status_consumer: Optional[StatusConsumer] = None

@app.on_event("startup")
async def startup():
    # ... your existing startup code remains unchanged ...
    pass

@app.on_event("shutdown")
async def shutdown():
    # ... your existing shutdown code remains unchanged ...
    pass