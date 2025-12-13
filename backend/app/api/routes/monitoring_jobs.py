"""
API endpoints for managing monitoring jobs
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.database import get_db
from app.api.deps import get_current_user
from app.models.monitoring_job import MonitoringJob, MonitoringJobStatus
from app.services.scheduler import MonitoringScheduler
import logging
import uuid
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["monitoring_jobs"])

# Global scheduler instance (set by main.py on startup)
_scheduler: Optional[MonitoringScheduler] = None

def set_scheduler(scheduler: MonitoringScheduler):
    """Set the global scheduler instance"""
    global _scheduler
    _scheduler = scheduler

def _get_user_uuid(user_id_str: str) -> uuid.UUID:
    """Convert user_id string to UUID, handling both UUID and string formats"""
    try:
        if isinstance(user_id_str, uuid.UUID):
            return user_id_str
        # Try parsing as UUID
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        # Fallback for string identifiers
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id_str)

@router.get("/monitoring/jobs")
async def list_monitoring_jobs(
    status: Optional[str] = Query(None, regex="^(active|paused|completed|failed)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List monitoring jobs for current user"""
    user_id_str = current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = _get_user_uuid(user_id_str)
    
    try:
        # Build query
        query = select(MonitoringJob).where(MonitoringJob.user_id == user_id)
        
        if status:
            query = query.where(MonitoringJob.status == MonitoringJobStatus(status))
        
        # Get total count
        count_result = await db.execute(
            select(func.count(MonitoringJob.id)).where(MonitoringJob.user_id == user_id)
        )
        total = count_result.scalar() or 0
        
        # Get paginated results
        result = await db.execute(
            query.order_by(MonitoringJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = result.scalars().all()
        
        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": [
                {
                    "id": str(j.id),
                    "target_url": j.target_url,
                    "interval_hours": j.interval_hours,
                    "status": j.status.value,
                    "total_checks": j.total_checks,
                    "findings_count": j.findings_count,
                    "alerts_triggered": j.alerts_triggered,
                    "last_run_at": j.last_run_at.isoformat() if j.last_run_at else None,
                    "next_run_at": j.next_run_at.isoformat() if j.next_run_at else None,
                    "created_at": j.created_at.isoformat()
                }
                for j in jobs
            ]
        }
    
    except Exception as e:
        logger.error(f"[Jobs] List failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")

@router.get("/monitoring/jobs/{job_id}")
async def get_monitoring_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific monitoring job"""
    user_id_str = current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = _get_user_uuid(user_id_str)
    
    try:
        result = await db.execute(
            select(MonitoringJob).where(
                MonitoringJob.id == job_id,
                MonitoringJob.user_id == user_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "success": True,
            "job": {
                "id": str(job.id),
                "target_url": job.target_url,
                "interval_hours": job.interval_hours,
                "status": job.status.value,
                "total_checks": job.total_checks,
                "findings_count": job.findings_count,
                "alerts_triggered": job.alerts_triggered,
                "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
                "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Get detail failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job")

@router.post("/monitoring/jobs/{job_id}/pause")
async def pause_monitoring_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Pause a monitoring job"""
    user_id_str = current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = _get_user_uuid(user_id_str)
    
    if not _scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    
    try:
        result = await db.execute(
            select(MonitoringJob).where(
                MonitoringJob.id == job_id,
                MonitoringJob.user_id == user_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        await _scheduler.pause_job(job_id)
        
        return {
            "success": True,
            "message": f"Monitoring job {job_id} paused",
            "status": "paused"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Pause failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause job")

@router.post("/monitoring/jobs/{job_id}/resume")
async def resume_monitoring_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused monitoring job"""
    user_id_str = current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = _get_user_uuid(user_id_str)
    
    if not _scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    
    try:
        result = await db.execute(
            select(MonitoringJob).where(
                MonitoringJob.id == job_id,
                MonitoringJob.user_id == user_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        await _scheduler.resume_job(job_id)
        
        return {
            "success": True,
            "message": f"Monitoring job {job_id} resumed",
            "status": "active"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Resume failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume job")

@router.delete("/monitoring/jobs/{job_id}")
async def delete_monitoring_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a monitoring job"""
    user_id_str = current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = _get_user_uuid(user_id_str)
    
    if not _scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    
    try:
        result = await db.execute(
            select(MonitoringJob).where(
                MonitoringJob.id == job_id,
                MonitoringJob.user_id == user_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        await _scheduler.delete_job(job_id)
        
        return {
            "success": True,
            "message": f"Monitoring job {job_id} deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Delete failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete job")
