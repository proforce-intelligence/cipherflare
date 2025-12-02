from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.services.kafka_producer import KafkaProducer
from app.api.deps import get_current_user
from app.models.alert import Alert
from sqlalchemy import select, delete
import logging
import uuid
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["monitoring"])

kafka_producer = None

def get_kafka():
    global kafka_producer
    if not kafka_producer:
        kafka_producer = KafkaProducer()
    return kafka_producer

@router.post("/monitor/target")
async def setup_target_monitoring(
    url: str = Query(..., min_length=5),
    interval_hours: int = Query(6, ge=1, le=720),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Setup continuous monitoring of a specific .onion URL
    """
    try:
        user_id = current_user.get("sub") if current_user else None
        job_id = str(uuid.uuid4())
        
        # Queue monitoring job to Kafka
        kafka = get_kafka()
        job_payload = {
            "job_id": job_id,
            "url": url,
            "interval_hours": interval_hours,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "job_type": "monitor"
        }
        
        await kafka.produce("monitor_jobs", job_payload)
        logger.info(f"[v0] Queued monitor job {job_id} for URL: {url}")
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Monitoring setup for {url} every {interval_hours} hours",
            "monitor_config": {
                "url": url,
                "interval_hours": interval_hours,
                "created_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Monitor setup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Monitor setup failed")

@router.post("/alert/setup")
async def setup_alert(
    keyword: str = Query(..., min_length=1),
    risk_threshold: str = Query("medium", regex="^(low|medium|high|critical)$"),
    notification_type: str = Query("email", regex="^(email|webhook)$"),
    notification_endpoint: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Setup alert for keyword findings above risk threshold
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = current_user.get("sub")
        
        alert = Alert(
            user_id=user_id,
            keyword=keyword,
            risk_level_threshold=risk_threshold,
            notification_type=notification_type,
            notification_endpoint=notification_endpoint,
            is_active=True
        )
        
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        
        logger.info(f"[v0] Alert created for keyword: {keyword}")
        
        return {
            "success": True,
            "alert_id": str(alert.id),
            "keyword": keyword,
            "risk_threshold": risk_threshold
        }
    except Exception as e:
        logger.error(f"Alert setup failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Alert setup failed")

@router.get("/alerts")
async def get_user_alerts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all alerts for current user
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = current_user.get("sub")
        
        result = await db.execute(
            select(Alert).where(Alert.user_id == user_id).where(Alert.is_active == True)
        )
        alerts = result.scalars().all()
        
        return {
            "success": True,
            "alerts": [
                {
                    "id": str(a.id),
                    "keyword": a.keyword,
                    "risk_threshold": a.risk_level_threshold,
                    "notification_type": a.notification_type
                }
                for a in alerts
            ]
        }
    except Exception as e:
        logger.error(f"Alert retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

@router.delete("/alert/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        result = await db.execute(
            delete(Alert).where(Alert.id == alert_id)
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"success": True, "message": "Alert deleted"}
    except Exception as e:
        logger.error(f"Alert deletion failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete alert")
