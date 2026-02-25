# verify_monitoring_scheduler.py
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.services.scheduler import MonitoringScheduler
from app.database.database import init_db
from app.models.monitoring_job import MonitoringJob, MonitoringJobStatus
from app.services.kafka_producer import KafkaProducer

async def verify_scheduler():
    # Initialize DB
    await init_db()
    
    # Setup scheduler
    scheduler = MonitoringScheduler()
    await scheduler.initialize()
    
    # Mock Kafka producer to avoid actual connection errors if kafka isn't up in this context
    # In a real test we'd want kafka, but for checking SCHEDULER logic, we mock the run method
    
    run_called = False
    
    async def mock_run_job(job_id, url, user_id):
        nonlocal run_called
        print(f"✅ Job {job_id} executed for {url}")
        run_called = True

    # Override the run method
    scheduler.run_monitoring_job = mock_run_job
    
    scheduler.scheduler.start()
    
    # Create a dummy job
    job_id = uuid.uuid4()
    job = MonitoringJob(
        id=job_id,
        user_id=uuid.uuid4(),
        target_url="http://test.onion",
        interval_hours=1,
        status=MonitoringJobStatus.ACTIVE
    )
    
    print(f"Scheduling job {job_id} to run in 2 seconds...")
    
    # Schedule it
    scheduler.scheduler.add_job(
        scheduler.run_monitoring_job,
        'date',
        run_date=datetime.now() + timedelta(seconds=2),
        args=[str(job.id), job.target_url, str(job.user_id)]
    )
    
    # Wait for execution
    await asyncio.sleep(5)
    
    if run_called:
        print("SUCCESS: Scheduler executed the job.")
    else:
        print("FAILURE: Scheduler did not execute the job.")
        
    await scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(verify_scheduler())
