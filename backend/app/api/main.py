from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.api.routes import search, monitor
from app.database.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dark Web Threat Intelligence API",
    description="Production-grade dark web monitoring and searching",
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

# Include routers
app.include_router(search.router)
app.include_router(monitor.router)

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    try:
        await init_db()
        logger.info("[✓] Database initialized")
    except Exception as e:
        logger.error(f"[!] Database initialization failed: {e}")

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
        "docs": "/docs"
    }
