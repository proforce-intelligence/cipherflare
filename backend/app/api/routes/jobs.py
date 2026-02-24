"""
Enhanced jobs API with progress tracking and alerts
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database.database import get_db
from app.api.deps import get_current_user
from app.models.job import Job, JobStatus, JobType
from app.services.kafka_producer import KafkaProducer
from app.services.es_client import ESClient
import logging
import uuid
import json
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["jobs"])

_kafka_producer: Optional[KafkaProducer] = None
_es_client: Optional[ESClient] = None

async def get_kafka() -> KafkaProducer:
    """Lazy-load Kafka producer"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducer()
        await _kafka_producer.connect()
    return _kafka_producer

def get_es() -> ESClient:
    """Get Elasticsearch client"""
    global _es_client
    if _es_client is None:
        _es_client = ESClient()
    return _es_client

def _get_user_uuid(user_id_str: str) -> uuid.UUID:
    """Convert user_id string to UUID"""
    try:
        if isinstance(user_id_str, uuid.UUID):
            return user_id_str
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id_str)

@router.post("/jobs/search")
async def create_search_job(
    keyword: str = Query(..., min_length=1, max_length=255),
    job_name: Optional[str] = Query(None, description="Human-readable job name"),
    max_results: int = Query(100, ge=1, le=10000),
    depth: int = Query(2, ge=1, le=5, description="Crawl depth (1-5)"),
    timeout_seconds: int = Query(30, ge=10, le=300, description="Per-page timeout"),
    include_summary: bool = Query(False),
    model_choice: str = Query("gemini-2.5-flash"),
    pgp_verify: bool = Query(False),
    report_type: str = Query("threat_intel"),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaProducer = Depends(get_kafka)
):
    """
    Create a new dark web search job with progress tracking
    """
    try:
        user_id = None  # For now, allow anonymous searches
        
        job_id = str(uuid.uuid4())
        
        # Generate job name if not provided
        if not job_name:
            job_name = f"Search: {keyword[:50]}"
        
        # Create job record
        job = Job(
            id=uuid.UUID(job_id),
            user_id=_get_user_uuid(user_id) if user_id else None,
            job_type=JobType.AD_HOC,
            status=JobStatus.QUEUED,
            keyword=keyword,
            max_results=max_results,
            payload=json.dumps({"report_type": report_type}) if report_type else None
        )
        
        db.add(job)
        await db.commit()
        
        # Queue job to Kafka
        job_payload = {
            "job_id": job_id,
            "job_name": job_name,
            "keyword": keyword,
            "max_results": max_results,
            "depth": depth,
            "timeout_seconds": timeout_seconds,
            "include_summary": include_summary,
            "model_choice": model_choice,
            "pgp_verify": pgp_verify,
            "report_type": report_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "job_type": "ad_hoc"
        }
        
        await kafka.produce("ad_hoc_jobs", job_payload)
        logger.info(f"[Jobs] Created search job {job_id}: {job_name}")
        
        return {
            "success": True,
            "job_id": job_id,
            "job_name": job_name,
            "keyword": keyword,
            "status": "queued",
            "message": "Search job created successfully",
            "estimated_time": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"[Jobs] Creation failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List all jobs with their current status and progress
    """
    try:
        # Build query
        query = select(Job)
        
        if status:
            query = query.where(Job.status == JobStatus(status.upper()))
        
        if job_type:
            query = query.where(Job.job_type == JobType(job_type))
        
        # Get total count
        count_result = await db.execute(select(func.count(Job.id)))
        total = count_result.scalar() or 0
        
        # Get paginated results
        result = await db.execute(
            query.order_by(desc(Job.created_at))
            .limit(limit)
            .offset(offset)
        )
        jobs = result.scalars().all()
        
        # Calculate progress for each job
        jobs_data = []
        for job in jobs:
            progress = 0
            if job.status == JobStatus.COMPLETED:
                progress = 100
            elif job.status == JobStatus.PROCESSING:
                # Estimate based on findings count vs max_results
                if job.max_results > 0:
                    progress = min(95, int((job.findings_count / job.max_results) * 100))
                else:
                    progress = 50  # Unknown progress
            elif job.status == JobStatus.FAILED:
                progress = 0
            
            # Calculate duration
            duration = None
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
            elif job.started_at:
                duration = (datetime.utcnow() - job.started_at).total_seconds()
            
            jobs_data.append({
                "id": str(job.id),
                "job_name": f"Search: {job.keyword}" if job.keyword else f"Monitor: {job.target_url}",
                "keyword": job.keyword,
                "target_url": job.target_url,
                "job_type": job.job_type.value,
                "status": job.status.value.lower(),
                "progress": progress,
                "findings_count": job.findings_count,
                "max_results": job.max_results,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration_seconds": duration,
                "error_message": job.error_message
            })
        
        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": jobs_data
        }
        
    except Exception as e:
        logger.error(f"[Jobs] List failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")

@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed status and progress of a specific job
    """
    try:
        try:
            job_uuid = uuid.UUID(job_id)
        except (ValueError, AttributeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid job ID format: {str(e)}")
        
        result = await db.execute(
            select(Job).where(Job.id == job_uuid)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Calculate progress
        progress = 0
        if job.status == JobStatus.COMPLETED:
            progress = 100
        elif job.status == JobStatus.PROCESSING:
            if job.max_results > 0:
                progress = min(95, int((job.findings_count / job.max_results) * 100))
            else:
                progress = 50
        
        # Calculate duration
        duration = None
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
        elif job.started_at:
            duration = (datetime.utcnow() - job.started_at).total_seconds()
        
        return {
            "success": True,
            "job": {
                "id": str(job.id),
                "job_name": f"Search: {job.keyword}" if job.keyword else f"Monitor: {job.target_url}",
                "keyword": job.keyword,
                "target_url": job.target_url,
                "job_type": job.job_type.value,
                "status": job.status.value.lower(),
                "progress": progress,
                "findings_count": job.findings_count,
                "max_results": job.max_results,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration_seconds": duration,
                "error_message": job.error_message,
                "ai_report": job.ai_report
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Get status failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")

@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_summary: bool = Query(False),
    model_choice: str = Query("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get results for a completed job
    """
    try:
        try:
            job_uuid = uuid.UUID(job_id)
        except (ValueError, AttributeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid job ID format: {str(e)}")
        
        # Check if job exists and is completed
        result = await db.execute(
            select(Job).where(Job.id == job_uuid)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get findings from Elasticsearch
        es = get_es()
        findings = await es.search_by_job_id(job_id)
        
        # Pagination
        total = len(findings)
        paginated = findings[offset:offset+limit]
        
        # Get summary: prefer stored ai_report, fallback to generating new one if requested
        summary = job.ai_report
        if not summary and include_summary and findings:
            from app.services.llm_summarizer import generate_findings_summary
            summary_data = await generate_findings_summary(
                job.keyword or job_id,
                findings,
                model_choice=model_choice
            )
            if summary_data and summary_data.get("success"):
                summary = summary_data.get("summary")
        
        return {
            "success": True,
            "job_id": job_id,
            "job_name": f"Search: {job.keyword}" if job.keyword else f"Monitor: {job.target_url}",
            "status": job.status.value.lower(),
            "total_findings": total,
            "offset": offset,
            "limit": limit,
            "findings": paginated,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Get results failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job results")

@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Pause a running or queued job"""
    try:
        job_uuid = uuid.UUID(job_id)
        result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in [JobStatus.QUEUED, JobStatus.PROCESSING]:
            raise HTTPException(status_code=400, detail=f"Cannot pause job in {job.status} state")
            
        job.status = JobStatus.PAUSED
        await db.commit()
        return {"success": True, "message": "Job paused"}
    except Exception as e:
        logger.error(f"Pause failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    kafka: KafkaProducer = Depends(get_kafka)
):
    """Resume a paused job"""
    try:
        job_uuid = uuid.UUID(job_id)
        result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.PAUSED:
            raise HTTPException(status_code=400, detail="Only paused jobs can be resumed")
            
        job.status = JobStatus.QUEUED
        await db.commit()
        
        # Re-queue to Kafka
        job_payload = {
            "job_id": str(job.id),
            "keyword": job.keyword,
            "max_results": job.max_results,
            "user_id": str(job.user_id) if job.user_id else None,
            "job_type": "ad_hoc",
            "is_resume": True
        }
        await kafka.produce("ad_hoc_jobs", job_payload)
        
        return {"success": True, "message": "Job resumed and re-queued"}
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a job. If active, it signals the worker to stop by setting status to DELETED.
    """
    try:
        try:
            job_uuid = uuid.UUID(job_id)
        except (ValueError, AttributeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid job ID format: {str(e)}")
        
        result = await db.execute(
            select(Job).where(Job.id == job_uuid)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # If job is active, we set it to DELETED so worker stops.
        # It will be physically deleted from DB later or handled by cleanup task.
        if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.PAUSED]:
            job.status = JobStatus.DELETED
            await db.commit()
            return {
                "success": True,
                "message": f"Job {job_id} marked for deletion. Worker will stop processing it."
            }
        
        await db.delete(job)
        await db.commit()
        
        logger.info(f"[Jobs] Deleted job {job_id}")
        return {
            "success": True,
            "message": f"Job {job_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Jobs] Delete failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete job")
