from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database.database import get_db
from app.models.evidence import Evidence
from app.models.case import Case
from app.models.dark_web import DarkWebMonitor, DarkWebAlert, DarkWebFinding
from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from datetime import datetime, timedelta
import logging
import json
import asyncio
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from app.services.dark_web_scraper import search_ahmia, scrape_onion_page, extract_entities, find_keyword_context
from playwright.async_api import async_playwright
from app.services.es_client import search_findings, get_job_findings
from app.services.kafka_utils import send_job
from uuid import uuid4
from app.models.dark_web import DarkWebSearchRequest, DarkWebMonitorRequest, DarkWebResult

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/search")
async def hybrid_search(request: DarkWebSearchRequest, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    job_id = f"job-{uuid4().hex[:8]}"
    
    # Instant ES search
    indexed = await search_findings(request.keyword)
    
    # Queue async scrape
    payload = {
        "job_id": job_id,
        "type": "ad_hoc",
        "keyword": request.keyword,
        "max_results": request.max_results,
        "depth": request.depth,
        "user_id": user.id
    }
    asyncio.create_task(send_job("ad_hoc_jobs", payload))
    
    return {
        "success": True,
        "job_id": job_id,
        "indexed_findings": indexed,
        "message": f"Displaying {len(indexed)} pre-indexed findings. Deep scrape queued (Job {job_id})."
    }

@router.post("/monitor")
async def setup_monitoring(request: DarkWebMonitorRequest, db: Session = Depends(get_db)):
    monitor = DarkWebMonitor(
        user_id=None,  # As per your code
        name=request.monitor_name,
        keywords=request.keywords,
        alert_threshold=request.alert_threshold,
        status="active",
        next_scan=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return {"success": True, "monitor_id": monitor.id}

@router.get("/monitors")
async def get_monitors(db: Session = Depends(get_db)):
    monitors = db.query(DarkWebMonitor).order_by(desc(DarkWebMonitor.created_at)).all()
    return {"monitors": [m.__dict__ for m in monitors]}

@router.get("/files/screenshot/{file_path:path}")
async def serve_screenshot(file_path: str):
    full_path = Path("/app/dark_web_files") / file_path
    if not full_path.exists() or full_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.gif']:
        raise HTTPException(404, "File not found")
    return FileResponse(str(full_path), media_type="image/png")

@router.get("/files/text/{file_path:path}")
async def serve_text_file(file_path: str):
    full_path = Path("/app/dark_web_files") / file_path
    if not full_path.exists() or full_path.suffix.lower() not in ['.txt', '.html', '.json']:
        raise HTTPException(404, "File not found")
    return FileResponse(str(full_path), media_type="text/plain")

@router.get("/findings/job/{job_id}")
async def get_job_results(job_id: str):
    return {"findings": await get_job_findings(job_id)}

@router.get("/findings/search")
async def findings_search(keyword: str):
    return {"results": await search_findings(keyword)}

@router.get("/stats")
async def get_dark_web_stats(db: Session = Depends(get_db)):
    # Your original + ES count
    total_findings = (await es_client.count(index="dark_web_findings"))["count"]
    monitors = db.query(DarkWebMonitor).all()
    return {
        "total_findings": total_findings,
        "active_monitors": len([m for m in monitors if m.status == "active"]),
        # ... your other stats
    }

# Your other endpoints like pause/resume/delete monitor, export, alerts - as in your original code
@router.post("/monitoring/{monitor_id}/pause")
async def pause_monitor(monitor_id: str, db: Session = Depends(get_db)):
    monitor = db.query(DarkWebMonitor).filter(DarkWebMonitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(404, "Not found")
    monitor.status = "paused"
    db.commit()
    return {"success": True, "status": "paused"}

# Similarly for resume, delete, etc.