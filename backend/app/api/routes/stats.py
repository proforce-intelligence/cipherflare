"""
Real-time statistics endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional  # Added missing Optional import
from app.database.database import get_db
from app.models.job import Job, JobStatus
from app.models.monitoring_result import MonitoringResult
from app.models.monitoring_job import MonitoringJob, MonitoringJobStatus
from app.services.es_client import ESClient
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["stats"])

_es_client: Optional[ESClient] = None

def get_es() -> ESClient:
    """Get Elasticsearch client"""
    global _es_client
    if _es_client is None:
        _es_client = ESClient()
    return _es_client

@router.get("/stats/realtime")
async def get_realtime_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time statistics for dashboard
    """
    try:
        # Job statistics
        total_jobs_result = await db.execute(
            select(func.count(Job.id))
        )
        total_jobs = total_jobs_result.scalar() or 0
        
        active_jobs_result = await db.execute(
            select(func.count(Job.id))
            .where(Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]))
        )
        active_jobs = active_jobs_result.scalar() or 0
        
        completed_jobs_result = await db.execute(
            select(func.count(Job.id))
            .where(Job.status == JobStatus.COMPLETED)
        )
        completed_jobs = completed_jobs_result.scalar() or 0
        
        # Monitoring statistics
        active_monitors_result = await db.execute(
            select(func.count(MonitoringJob.id))
            .where(MonitoringJob.status == MonitoringJobStatus.ACTIVE)
        )
        active_monitors = active_monitors_result.scalar() or 0
        
        # Threat statistics
        total_threats_result = await db.execute(
            select(func.count(MonitoringResult.id))
        )
        total_threats = total_threats_result.scalar() or 0
        
        high_risk_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(MonitoringResult.risk_level.in_(["high", "critical"]))
        )
        high_risk_threats = high_risk_result.scalar() or 0
        
        # Recent activity (last 24 hours)
        since_yesterday = datetime.utcnow() - timedelta(days=1)
        
        recent_jobs_result = await db.execute(
            select(func.count(Job.id))
            .where(Job.created_at >= since_yesterday)
        )
        recent_jobs = recent_jobs_result.scalar() or 0
        
        recent_threats_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(MonitoringResult.created_at >= since_yesterday)
        )
        recent_threats = recent_threats_result.scalar() or 0
        
        # Get findings count from Elasticsearch
        try:
            es = get_es()
            es_stats = await es.get_stats()
            total_findings = es_stats.get("total_findings", 0)
        except:
            total_findings = 0
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "jobs": {
                    "total": total_jobs,
                    "active": active_jobs,
                    "completed": completed_jobs,
                    "recent_24h": recent_jobs
                },
                "monitoring": {
                    "active_monitors": active_monitors,
                    "total_threats": total_threats,
                    "high_risk": high_risk_threats,
                    "recent_24h": recent_threats
                },
                "findings": {
                    "total_indexed": total_findings
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[Stats] Realtime stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get realtime stats")

@router.get("/stats/activity")
async def get_activity_timeline(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity timeline for charts
    """
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get recent jobs
        jobs_result = await db.execute(
            select(Job)
            .where(Job.created_at >= since_date)
            .order_by(Job.created_at.desc())
            .limit(20)
        )
        jobs = jobs_result.scalars().all()
        
        # Get recent threats
        threats_result = await db.execute(
            select(MonitoringResult)
            .where(MonitoringResult.created_at >= since_date)
            .order_by(MonitoringResult.created_at.desc())
            .limit(20)
        )
        threats = threats_result.scalars().all()
        
        # Combine and format activity
        activity = []
        
        for job in jobs:
            activity.append({
                "id": str(job.id),
                "type": "job",
                "action": f"Search job {'completed' if job.status == JobStatus.COMPLETED else 'started'}",
                "details": f"Keyword: {job.keyword}" if job.keyword else "Monitoring job",
                "status": job.status.value.lower(),
                "timestamp": job.created_at.isoformat()
            })
        
        for threat in threats:
            activity.append({
                "id": str(threat.id),
                "type": "threat",
                "action": f"Threat detected ({threat.risk_level})",
                "details": threat.title or "Unknown threat",
                "severity": threat.risk_level,
                "timestamp": threat.created_at.isoformat()
            })
        
        # Sort by timestamp
        activity.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "success": True,
            "period_days": days,
            "activity": activity[:50]  # Limit to 50 most recent
        }
        
    except Exception as e:
        logger.error(f"[Stats] Activity timeline failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get activity timeline")
