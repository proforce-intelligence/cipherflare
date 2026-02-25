"""
Status Consumer - Listens to Kafka status_updates topic and updates Job database records
"""
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.kafka_consumer import KafkaConsumer
from app.database.database import AsyncSessionLocal
from app.models.job import Job, JobStatus

logger = logging.getLogger(__name__)

class StatusConsumer:
    """
    Consumes status updates from Kafka and updates Job records in the database
    """
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.consumer = KafkaConsumer(
            topics=["status_updates"],
            group_id="status-updater",
            bootstrap_servers=bootstrap_servers
        )
    
    async def update_job_status(self, job_id: str, status: str, details: dict = None):
        """
        Update job status in database
        """
        try:
            job_uuid = uuid.UUID(job_id)
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Job).where(Job.id == job_uuid)
                )
                job = result.scalar_one_or_none()
                
                if not job:
                    logger.warning(f"[StatusConsumer] Job {job_id} not found in database")
                    return
                
                # Update status
                old_status = job.status.value if job.status else "UNKNOWN"
                job.status = JobStatus(status.upper())
                
                # Update timestamps based on status
                if status.upper() == "PROCESSING" and not job.started_at:
                    job.started_at = datetime.utcnow()
                    logger.info(f"[StatusConsumer] Job {job_id} started")
                
                elif status.upper() in ["COMPLETED", "FAILED"]:
                    if not job.started_at:
                        job.started_at = datetime.utcnow()
                    job.completed_at = datetime.utcnow()
                    logger.info(f"[StatusConsumer] Job {job_id} {status.lower()}")
                
                if details:
                    if "findings_count" in details:
                        job.findings_count = details["findings_count"]
                    if "sites_scraped" in details:
                        job.findings_count = details["sites_scraped"]  # Use sites_scraped as scraped count
                    if "total_sites" in details:
                        job.max_results = details["total_sites"]  # Update total sites
                    if "error" in details:
                        job.error_message = details["error"]
                    if "ai_report" in details:
                        job.ai_report = details["ai_report"]
                
                await db.commit()
                
                progress_info = ""
                if details and "sites_scraped" in details and "total_sites" in details:
                    progress_info = f" (progress: {details.get('sites_scraped')}/{details.get('total_sites')})"
                
                logger.info(
                    f"[StatusConsumer] Updated job {job_id}: "
                    f"{old_status} -> {status.upper()} "
                    f"(findings: {job.findings_count}){progress_info}"
                )
                
        except Exception as e:
            logger.error(f"[StatusConsumer] Failed to update job {job_id}: {e}", exc_info=True)
    
    async def process_status_message(self, topic: str, message: dict):
        """
        Process incoming status update message
        """
        try:
            job_id = message.get("job_id")
            status = message.get("status")
            details = message.get("details", {})
            
            if not job_id or not status:
                logger.warning(f"[StatusConsumer] Invalid message: {message}")
                return
            
            logger.info(f"[StatusConsumer] Received status update: {job_id} -> {status}")
            await self.update_job_status(job_id, status, details)
            
        except Exception as e:
            logger.error(f"[StatusConsumer] Message processing error: {e}", exc_info=True)
    
    async def start(self):
        """
        Start consuming status updates
        """
        try:
            await self.consumer.connect()
            logger.info("[StatusConsumer] Started - listening for status updates...")
            await self.consumer.consume(self.process_status_message)
        except Exception as e:
            logger.error(f"[StatusConsumer] Consumer error: {e}", exc_info=True)
            raise
        finally:
            await self.consumer.close()
    
    async def stop(self):
        """
        Stop the consumer gracefully
        """
        await self.consumer.close()
        logger.info("[StatusConsumer] Stopped")


async def run_status_consumer():
    """
    Standalone function to run the status consumer
    """
    consumer = StatusConsumer()
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("[StatusConsumer] Interrupted by user")
        await consumer.stop()
    except Exception as e:
        logger.error(f"[StatusConsumer] Fatal error: {e}")
        await consumer.stop()
        raise


if __name__ == "__main__":
    import sys
    try:
        asyncio.run(run_status_consumer())
    except KeyboardInterrupt:
        logger.info("[StatusConsumer] Shutdown complete")
        sys.exit(0)
