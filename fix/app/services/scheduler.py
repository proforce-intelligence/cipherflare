import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import AsyncSessionLocal
from app.models.monitoring_job import MonitoringJob, MonitoringJobStatus
from app.services.kafka_producer import KafkaProducer
import uuid

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.kafka_producer: Optional[KafkaProducer] = None
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
    
    async def initialize(self):
        """Initialize scheduler and Kafka producer"""
        try:
            self.kafka_producer = KafkaProducer(self.bootstrap_servers)
            await self.kafka_producer.connect()
            logger.info("[Scheduler] Initialized")
        except Exception as e:
            logger.error(f"[Scheduler] Initialization failed: {e}")
            raise
    
    async def load_active_jobs(self):
        """Load active monitoring jobs and schedule them"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MonitoringJob).where(
                        MonitoringJob.status == MonitoringJobStatus.ACTIVE
                    )
                )
                jobs = result.scalars().all()
            
            logger.info(f"[Scheduler] Loading {len(jobs)} active monitoring jobs")
            
            for job in jobs:
                await self.schedule_job(job)
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to load jobs: {e}")
    
    async def schedule_job(self, monitoring_job: MonitoringJob):
        """Schedule a single monitoring job"""
        try:
            job_key = f"monitor_{monitoring_job.id}"
            
            # Remove existing job if present
            if self.scheduler.get_job(job_key):
                self.scheduler.remove_job(job_key)
            
            # Add new job
            self.scheduler.add_job(
                self.run_monitoring_job,
                trigger=IntervalTrigger(hours=monitoring_job.interval_hours),
                id=job_key,
                args=[monitoring_job.id, monitoring_job.target_url, monitoring_job.user_id],
                name=f"Monitor {monitoring_job.target_url}"
            )
            
            logger.info(f"[Scheduler] Scheduled job {monitoring_job.id} for {monitoring_job.target_url} (every {monitoring_job.interval_hours}h)")
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to schedule job {monitoring_job.id}: {e}")
    
    async def run_monitoring_job(self, job_id: str, url: str, user_id: str):
        """Execute monitoring job"""
        try:
            if not self.kafka_producer:
                raise Exception("Kafka producer not initialized")
            
            monitor_payload = {
                "job_id": str(uuid.uuid4()),
                "job_type": "monitor",
                "target_url": url,
                "monitor_job_id": job_id,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.kafka_producer.produce("monitor_jobs", monitor_payload)
            
            # Update last_run_at in database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MonitoringJob).where(MonitoringJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if job:
                    job.last_run_at = datetime.utcnow()
                    job.total_checks += 1
                    await db.commit()
            
            logger.info(f"[Scheduler] Executed monitoring job {job_id} for {url}")
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to execute job {job_id}: {e}")
    
    async def add_monitoring_job(self, url: str, user_id: str, interval_hours: int = 6) -> MonitoringJob:
        """Create and schedule a new monitoring job"""
        try:
            async with AsyncSessionLocal() as db:
                job = MonitoringJob(
                    user_id=user_id,
                    target_url=url,
                    interval_hours=interval_hours,
                    status=MonitoringJobStatus.ACTIVE,
                    next_run_at=datetime.utcnow() + timedelta(seconds=5),  # Run in 5 seconds
                    last_run_at=None
                )
                
                db.add(job)
                await db.commit()
                await db.refresh(job)
            
            # Schedule it
            await self.schedule_job(job)
            logger.info(f"[Scheduler] Created monitoring job {job.id} for {url}")
            
            return job
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to add job: {e}")
            raise
    
    async def pause_job(self, job_id: str):
        """Pause a monitoring job"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MonitoringJob).where(MonitoringJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if job:
                    job.status = MonitoringJobStatus.PAUSED
                    await db.commit()
            
            scheduler_job_key = f"monitor_{job_id}"
            if self.scheduler.get_job(scheduler_job_key):
                self.scheduler.remove_job(scheduler_job_key)
            
            logger.info(f"[Scheduler] Paused job {job_id}")
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to pause job: {e}")
    
    async def resume_job(self, job_id: str):
        """Resume a paused monitoring job"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MonitoringJob).where(MonitoringJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if job:
                    job.status = MonitoringJobStatus.ACTIVE
                    await db.commit()
            
            # Re-schedule
            await self.schedule_job(job)
            logger.info(f"[Scheduler] Resumed job {job_id}")
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to resume job: {e}")
    
    async def delete_job(self, job_id: str):
        """Delete a monitoring job"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MonitoringJob).where(MonitoringJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if job:
                    job.status = MonitoringJobStatus.COMPLETED
                    await db.commit()
            
            scheduler_job_key = f"monitor_{job_id}"
            if self.scheduler.get_job(scheduler_job_key):
                self.scheduler.remove_job(scheduler_job_key)
            
            logger.info(f"[Scheduler] Deleted job {job_id}")
        
        except Exception as e:
            logger.error(f"[Scheduler] Failed to delete job: {e}")
    
    async def start(self):
        """Start the scheduler"""
        try:
            await self.load_active_jobs()
            self.scheduler.start()
            logger.info("[Scheduler] Started")
        except Exception as e:
            logger.error(f"[Scheduler] Failed to start: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the scheduler"""
        try:
            self.scheduler.shutdown()
            if self.kafka_producer:
                await self.kafka_producer.close()
            logger.info("[Scheduler] Shutdown complete")
        except Exception as e:
            logger.error(f"[Scheduler] Shutdown error: {e}")
