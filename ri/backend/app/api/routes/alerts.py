"""
Alert management endpoints for dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database.database import get_db
from app.api.deps import get_current_user
from app.models.alert import Alert
from app.models.monitoring_result import MonitoringResult
import logging
import uuid
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["alerts"])

def _get_user_uuid(user_id_str: str) -> uuid.UUID:
    """Convert user_id string to UUID"""
    try:
        if isinstance(user_id_str, uuid.UUID):
            return user_id_str
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id_str)

@router.get("/alerts/dashboard")
async def get_dashboard_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, pattern="^(unread|read|all)$"),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alerts for dashboard display with filtering
    """
    try:
        # For now, return monitoring results as alerts
        # In production, you'd have a dedicated alerts table
        query = select(MonitoringResult)
        
        if severity:
            query = query.where(MonitoringResult.risk_level == severity)
        
        # Get total count
        count_result = await db.execute(
            select(func.count(MonitoringResult.id))
        )
        total = count_result.scalar() or 0
        
        # Get paginated results
        result = await db.execute(
            query.order_by(desc(MonitoringResult.created_at))
            .limit(limit)
            .offset(offset)
        )
        results = result.scalars().all()
        
        alerts_data = []
        for r in results:
            alerts_data.append({
                "id": str(r.id),
                "job_id": str(r.id),
                "job_name": r.title or "Unknown Job",
                "type": "threat_detected",
                "title": f"Threat Detected: {r.title or 'Unknown'}",
                "message": r.text_excerpt[:200] if r.text_excerpt else "No description available",
                "severity": r.risk_level if r.risk_level in ["info", "warning", "error", "success"] else "info",
                "created_at": r.created_at.isoformat(),
                "read": False,  # Could add read status to model
                "data": {
                    "risk_score": r.risk_score,
                    "source_url": r.target_url,
                    "threat_indicators": r.threat_indicators or [],
                    "is_duplicate": r.is_duplicate,
                    "triggered_alerts": r.alerts_triggered or []
                }
            })
        
        # Get stats
        unread_count = total  # All are unread for now
        high_severity_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(MonitoringResult.risk_level.in_(["high", "critical"]))
        )
        high_severity_count = high_severity_result.scalar() or 0
        
        return {
            "success": True,
            "total": total,
            "unread": unread_count,
            "high_severity": high_severity_count,
            "limit": limit,
            "offset": offset,
            "alerts": alerts_data  # Always returns array
        }
        
    except Exception as e:
        logger.error(f"[Alerts] Dashboard fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")

@router.get("/alerts")
async def get_alerts_simple(
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """
    Simplified alerts endpoint for backward compatibility
    Returns array directly
    """
    try:
        query = select(MonitoringResult)
        
        # Get paginated results
        result = await db.execute(
            query.order_by(desc(MonitoringResult.created_at))
            .limit(50)
        )
        results = result.scalars().all()
        
        alerts_data = []
        for r in results:
            alerts_data.append({
                "id": str(r.id),
                "job_id": str(r.id),
                "job_name": r.title or "Unknown Job",
                "type": "threat_detected",
                "title": f"Threat Detected: {r.title or 'Unknown'}",
                "message": r.text_excerpt[:200] if r.text_excerpt else "No description available",
                "severity": r.risk_level if r.risk_level in ["info", "warning", "error", "success"] else "info",
                "created_at": r.created_at.isoformat(),
                "read": False,
                "data": {
                    "risk_score": r.risk_score,
                    "source_url": r.target_url,
                    "threat_indicators": r.threat_indicators or [],
                }
            })
        
        return alerts_data
        
    except Exception as e:
        logger.error(f"[Alerts] Fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")

@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an alert as read
    """
    try:
        # In production, update alert read status
        return {
            "success": True,
            "message": "Alert marked as read"
        }
    except Exception as e:
        logger.error(f"[Alerts] Mark read failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark alert as read")

@router.post("/alerts/mark-all-read")
async def mark_all_alerts_read(
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all alerts as read
    """
    try:
        # In production, bulk update read status
        return {
            "success": True,
            "message": "All alerts marked as read"
        }
    except Exception as e:
        logger.error(f"[Alerts] Mark all read failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark all alerts as read")

@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert from dashboard
    """
    try:
        try:
            alert_uuid = uuid.UUID(alert_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid alert ID format")
        
        result = await db.execute(
            select(MonitoringResult).where(MonitoringResult.id == alert_uuid)
        )
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        await db.delete(record)
        await db.commit()
        
        return {
            "success": True,
            "message": "Alert deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Alerts] Delete failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete alert")

@router.get("/alerts/stats")
async def get_alert_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert statistics for dashboard
    """
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Total alerts
        total_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(MonitoringResult.created_at >= since_date)
        )
        total = total_result.scalar() or 0
        
        # By severity
        critical_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(
                MonitoringResult.created_at >= since_date,
                MonitoringResult.risk_level == "critical"
            )
        )
        critical = critical_result.scalar() or 0
        
        high_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(
                MonitoringResult.created_at >= since_date,
                MonitoringResult.risk_level == "high"
            )
        )
        high = high_result.scalar() or 0
        
        medium_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(
                MonitoringResult.created_at >= since_date,
                MonitoringResult.risk_level == "medium"
            )
        )
        medium = medium_result.scalar() or 0
        
        low_result = await db.execute(
            select(func.count(MonitoringResult.id))
            .where(
                MonitoringResult.created_at >= since_date,
                MonitoringResult.risk_level == "low"
            )
        )
        low = low_result.scalar() or 0
        
        return {
            "success": True,
            "period_days": days,
            "stats": {
                "total": total,
                "by_severity": {
                    "critical": critical,
                    "high": high,
                    "medium": medium,
                    "low": low
                },
                "unread": total  # All unread for now
            }
        }
        
    except Exception as e:
        logger.error(f"[Alerts] Stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert stats")
