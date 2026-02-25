from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text
from app.database.database import get_db
from app.services.kafka_producer import KafkaProducer
from app.api.deps import get_current_user
from app.models.alert import Alert
from app.models.monitoring_result import MonitoringResult
from app.services.crypto_utils import encrypt_credential  # Added encryption import
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["monitoring"])

# Global Kafka producer (reused across requests)
_kafka_producer: Optional[KafkaProducer] = None

async def get_kafka() -> KafkaProducer:
    """Lazy-load and reuse KafkaProducer instance"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducer()
        await _kafka_producer.connect()  # Ensure connection
    return _kafka_producer

def _get_user_uuid(user_id_str: str) -> uuid.UUID:
    """Convert user_id string to UUID, handling both UUID and string formats"""
    try:
        if isinstance(user_id_str, uuid.UUID):
            return user_id_str
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id_str)

# @router.post("/monitor/target")
# async def setup_target_monitoring(
#     title: str = Query(
#         ..., 
#         min_length=3, 
#         max_length=120, 
#         description="Unique title/name for this monitoring job (required)"
#     ),
#     url: str = Query(
#         ..., 
#         description="Full .onion URL to monitor", 
#         min_length=10, 
#         pattern=r"^http://.*\.onion"
#     ),
#     interval_hours: int = Query(6, ge=1, le=720, description="Check interval in hours"),
#     username: Optional[str] = Query(None, description="Username for site authentication (if required)"),
#     password: Optional[str] = Query(None, description="Password for site authentication (if required)"),
#     login_path: Optional[str] = Query(None, description="Relative path to login page (e.g., '/login')"),
#     username_selector: Optional[str] = Query(None, description="CSS selector for username field"),
#     password_selector: Optional[str] = Query(None, description="CSS selector for password field"),
#     submit_selector: Optional[str] = Query(None, description="CSS selector for submit button"),
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
#     kafka: KafkaProducer = Depends(get_kafka)
# ):
#     """
#     Setup continuous monitoring of a specific .onion URL
#     Supports optional authentication for sites requiring login
#     """
#     user_id = current_user.get("sub")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     if (username and not password) or (password and not username):
#         raise HTTPException(
#             status_code=400,
#             detail="Both username and password must be provided for authentication"
#         )
# 
#     # Check if title is unique for this user
#     title_normalized = title.strip()
#     existing = await db.execute(
#         select(MonitoringJob)
#         .where(MonitoringJob.user_id == _get_user_uuid(user_id))
#         .where(MonitoringJob.title == title_normalized)
#     )
#     if existing.scalar_one_or_none():
#         raise HTTPException(
#             status_code=400,
#             detail=f"A monitoring job with title '{title}' already exists for your account"
#         )
# 
#     job_id = str(uuid.uuid4())
# 
#     encrypted_username = None
#     encrypted_password = None
#     
#     if username and password:
#         try:
#             encrypted_username = encrypt_credential(username)
#             encrypted_password = encrypt_credential(password)
#             logger.info(f"[Monitor] Encrypted credentials for job {job_id}")
#         except Exception as e:
#             logger.error(f"[Monitor] Credential encryption failed: {e}")
#             raise HTTPException(status_code=500, detail="Failed to encrypt credentials")
# 
#     payload = {
#         "job_id": job_id,
#         "job_type": "monitor",
#         "title": title_normalized,  # ← added
#         "target_url": url.strip(),
#         "interval_hours": interval_hours,
#         "user_id": user_id,
#         "auth_username": encrypted_username,
#         "auth_password": encrypted_password,
#         "login_path": login_path,
#         "username_selector": username_selector or 'input[name="username"], input[id="username"], input[type="text"]',
#         "password_selector": password_selector or 'input[name="password"], input[id="password"], input[type="password"]',
#         "submit_selector": submit_selector or 'button[type="submit"], input[type="submit"], button[name="login"]',
#         "created_at": datetime.now(timezone.utc).isoformat(),
#         "next_run_at": datetime.now(timezone.utc).isoformat()
#     }
# 
#     await kafka.produce("monitor_jobs", payload)
#     logger.info(f"[Monitor] Queued monitor job {job_id} '{title}' for {url} (auth: {bool(username)})")
# 
#     return {
#         "success": True,
#         "job_id": job_id,
#         "title": title_normalized,  # ← returned
#         "message": f"Monitoring started for '{title}' → {url}",
#         "config": {
#             "title": title_normalized,
#             "url": url,
#             "interval_hours": interval_hours,
#             "user_id": user_id,
#             "requires_auth": bool(username),
#             "status": "active"
#         }
#     }
# 
# @router.post("/alert/setup")
# async def setup_alert(
#     keyword: str = Query(..., min_length=2, max_length=100, description="Keyword to monitor"),
#     risk_threshold: str = Query(
#         "medium",
#         pattern="^(low|medium|high|critical)$",
#         description="Minimum risk level to trigger alert"
#     ),
#     notification_type: str = Query(
#         "email",
#         pattern="^(email|webhook|slack)$",
#         description="How to notify"
#     ),
#     notification_endpoint: Optional[str] = Query(
#         None,
#         description="Email address or webhook URL (required for email/webhook)"
#     ),
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Create a real-time alert for high-risk findings
#     """
#     user_id_str = current_user.get("sub")
#     if not user_id_str:
#         raise HTTPException(status_code=401, detail="Authentication required")
#     
#     user_id = _get_user_uuid(user_id_str)
# 
#     if notification_type in ["email", "webhook", "slack"] and not notification_endpoint:
#         raise HTTPException(
#             status_code=400,
#             detail=f"{notification_type} requires notification_endpoint"
#         )
# 
#     try:
#         alert = Alert(
#             user_id=user_id,
#             keyword=keyword.strip().lower(),
#             risk_level_threshold=risk_threshold,
#             notification_type=notification_type,
#             notification_endpoint=notification_endpoint.strip() if notification_endpoint else None,
#             is_active=True,
#             created_at=datetime.now(timezone.utc)
#         )
# 
#         db.add(alert)
#         await db.commit()
#         await db.refresh(alert)
# 
#         logger.info(f"[Alert] Created alert {alert.id} for '{keyword}' → {risk_threshold}+")
# 
#         return {
#             "success": True,
#             "alert_id": str(alert.id),
#             "keyword": keyword,
#             "risk_threshold": risk_threshold,
#             "notification_type": notification_type,
#             "status": "active",
#             "created_at": alert.created_at.isoformat()
#         }
# 
#     except Exception as e:
#         logger.error(f"[Alert] Creation failed: {e}")
#         await db.rollback()
#         raise HTTPException(status_code=500, detail="Failed to create alert")
# 

@router.get("/alerts")
async def get_user_alerts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all active alerts for current user"""
    user_id_str = current_user.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = _get_user_uuid(user_id_str)

    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == user_id)
        .where(Alert.is_active == True)
        .order_by(Alert.created_at.desc())
    )
    alerts = result.scalars().all()

    return {
        "success": True,
        "count": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "keyword": a.keyword,
                "risk_threshold": a.risk_level_threshold,
                "notification_type": a.notification_type,
                "notification_endpoint": a.notification_endpoint,
                "created_at": a.created_at.isoformat(),
                "is_active": a.is_active
            }
            for a in alerts
        ]
    }


# @router.delete("/alert/{alert_id}")
# async def delete_alert(
#     alert_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Delete (deactivate) an alert"""
#     try:
#         user_id_str = current_user.get("sub")
#         if not user_id_str:
#             raise HTTPException(status_code=401, detail="Authentication required")
# 
#         user_id = _get_user_uuid(user_id_str)
# 
#         result = await db.execute(
#             select(Alert).where(Alert.id == alert_id)
#         )
#         alert = result.scalar_one_or_none()
# 
#         if not alert:
#             raise HTTPException(status_code=404, detail="Alert not found")
# 
#         if alert.user_id != user_id:
#             raise HTTPException(status_code=403, detail="Not authorized")
# 
#         alert.is_active = False
#         if hasattr(alert, 'deactivated_at'):
#             alert.deactivated_at = datetime.now(timezone.utc)
#         await db.commit()
# 
#         logger.info(f"[Alert] Deactivated alert {alert_id}")
#         return {"success": True, "message": "Alert deactivated"}
# 
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"[Alert] Delete failed: {e}")
#         await db.rollback()
#         raise HTTPException(status_code=500, detail="Failed to delete alert")

# @router.get("/monitoring/results")
# async def get_monitoring_results(
#     limit: int = Query(50, ge=1, le=500),
#     offset: int = Query(0, ge=0),
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     user_id_str = current_user.get("sub")
#     if not user_id_str:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     user_id = _get_user_uuid(user_id_str)
# 
#     try:
#         count_result = await db.execute(
#             select(func.count(MonitoringResult.id)).where(
#                 MonitoringResult.user_id == user_id
#             )
#         )
#         total = count_result.scalar() or 0
# 
#         # Use raw column names instead of letting SQLAlchemy convert to UUID
#         result = await db.execute(
#             select(
#                 MonitoringResult.id.label("id_raw"),
#                 MonitoringResult.target_url,
#                 MonitoringResult.title,
#                 MonitoringResult.risk_level,
#                 MonitoringResult.risk_score,
#                 MonitoringResult.is_duplicate,
#                 MonitoringResult.alerts_triggered,
#                 MonitoringResult.created_at,
#                 MonitoringResult.detected_at,
#                 # Add other fields you need...
#             )
#             .where(MonitoringResult.user_id == user_id)
#             .order_by(MonitoringResult.created_at.desc())
#             .limit(limit)
#             .offset(offset)
#         )
# 
#         rows = result.all()
# 
#         def safe_uuid(val):
#             if val is None:
#                 return None
#             if isinstance(val, uuid.UUID):
#                 return str(val)
#             if isinstance(val, (int, str)):
#                 try:
#                     return str(uuid.UUID(int=val) if isinstance(val, int) else val)
#                 except ValueError:
#                     return str(val)  # fallback - return as string
#             return str(val)
# 
#         return {
#             "success": True,
#             "total": total,
#             "limit": limit,
#             "offset": offset,
#             "results": [
#                 {
#                     "id": safe_uuid(row.id_raw),
#                     "target_url": row.target_url,
#                     "title": row.title,
#                     "risk_level": row.risk_level,
#                     "risk_score": row.risk_score,
#                     "is_duplicate": row.is_duplicate,
#                     "alerts_triggered": row.alerts_triggered or [],
#                     "created_at": row.created_at.isoformat() if row.created_at else None,
#                     "detected_at": row.detected_at.isoformat() if row.detected_at else None,
#                 }
#                 for row in rows
#             ]
#         }
# 
#     except Exception as e:
#         logger.error(f"[Monitoring] Get results failed: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Failed to fetch results")
# 

# @router.get("/monitoring/results/{result_id}")
# async def get_monitoring_result_detail(
#     result_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     user_id_str = current_user.get("sub")
#     if not user_id_str:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     user_id = _get_user_uuid(user_id_str)
# 
#     # Raw SQL - no ORM UUID coercion issues
#     query = text("""
#         SELECT 
#             id,
#             target_url,
#             title,
#             text_excerpt,
#             risk_level,
#             risk_score,
#             threat_indicators,
#             content_hash,
#             is_duplicate,
#             alerts_triggered,@router.get("/monitoring/results/{result_id}")
# async def get_monitoring_result_detail(
#     result_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     user_id_str = current_user.get("sub")
#     if not user_id_str:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     user_id = _get_user_uuid(user_id_str)
# 
#     # Raw SQL - no ORM UUID coercion issues
#     query = text("""
#         SELECT 
#             id,
#             target_url,
#             title,
#             text_excerpt,
#             risk_level,
#             risk_score,
#             threat_indicators,
#             content_hash,@router.get("/monitoring/results/{result_id}")
# async def get_monitoring_result_detail(
#     result_id: str,
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     user_id_str = current_user.get("sub")
#     if not user_id_str:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     user_id = _get_user_uuid(user_id_str)
# 
#     # Raw SQL - no ORM UUID coercion issues
#     query = text("""
#         SELECT 
#             id,
#             target_url,
#             title,
#             text_excerpt,
#             risk_level,
#             risk_score,
#             threat_indicators,
#             content_hash,
#             is_duplicate,
#             alerts_triggered,
#             created_at,
#             detected_at
#         FROM monitoring_results
#         WHERE id = :result_id 
#           AND user_id = :user_id
#     """)
# 
#     result = await db.execute(
#         query,
#         {
#             "result_id": result_id,
#             "user_id": str(user_id)
#         }
#     )
# 
#     row = result.mappings().first()
# 
#     if not row:
#         raise HTTPException(status_code=404, detail="Monitoring result not found or not authorized")
# 
#     def safe_uuid(val):
#         if val is None:
#             return None
#         if isinstance(val, uuid.UUID):
#             return str(val)
#         if isinstance(val, str):
#             try:
#                 return str(uuid.UUID(val))
#             except ValueError:
#                 return val
#         return str(val)
# 
#     return {
#         "success": True,
#         "result": {
#             "id": safe_uuid(row["id"]),
#             "target_url": row["target_url"],
#             "title": row["title"],
#             "text_excerpt": row["text_excerpt"],
#             "risk_level": row["risk_level"],
#             "risk_score": row["risk_score"],
#             "threat_indicators": row["threat_indicators"],
#             "content_hash": row["content_hash"],
#             "is_duplicate": row["is_duplicate"],
#             "alerts_triggered": row["alerts_triggered"] or [],
#             "created_at": row["created_at"].isoformat() if row["created_at"] else None,
#             "detected_at": row["detected_at"].isoformat() if row["detected_at"] else None,
#         }
#     }
#             is_duplicate,
#             alerts_triggered,
#             created_at,
#             detected_at
#         FROM monitoring_results
#         WHERE id = :result_id 
#           AND user_id = :user_id
#     """)
# 
#     result = await db.execute(
#         query,
#         {
#             "result_id": result_id,
#             "user_id": str(user_id)
#         }
#     )
# 
#     row = result.mappings().first()
# 
#     if not row:
#         raise HTTPException(status_code=404, detail="Monitoring result not found or not authorized")
# 
#     def safe_uuid(val):
#         if val is None:
#             return None
#         if isinstance(val, uuid.UUID):
#             return str(val)
#         if isinstance(val, str):
#             try:
#                 return str(uuid.UUID(val))
#             except ValueError:
#                 return val
#         return str(val)
# 
#     return {
#         "success": True,
#         "result": {
#             "id": safe_uuid(row["id"]),
#             "target_url": row["target_url"],
#             "title": row["title"],
#             "text_excerpt": row["text_excerpt"],
#             "risk_level": row["risk_level"],
#             "risk_score": row["risk_score"],
#             "threat_indicators": row["threat_indicators"],
#             "content_hash": row["content_hash"],
#             "is_duplicate": row["is_duplicate"],
#             "alerts_triggered": row["alerts_triggered"] or [],
#             "created_at": row["created_at"].isoformat() if row["created_at"] else None,
#             "detected_at": row["detected_at"].isoformat() if row["detected_at"] else None,
#         }
#     }
#             created_at,
#             detected_at
#         FROM monitoring_results
#         WHERE id = :result_id 
#           AND user_id = :user_id
#     """)
# 
#     result = await db.execute(
#         query,
#         {
#             "result_id": result_id,
#             "user_id": str(user_id)
#         }
#     )
# 
#     row = result.mappings().first()
# 
#     if not row:
#         raise HTTPException(status_code=404, detail="Monitoring result not found or not authorized")
# 
#     def safe_uuid(val):
#         if val is None:
#             return None
#         if isinstance(val, uuid.UUID):
#             return str(val)
#         if isinstance(val, str):
#             try:
#                 return str(uuid.UUID(val))
#             except ValueError:
#                 return val
#         return str(val)
# 
#     return {
#         "success": True,
#         "result": {
#             "id": safe_uuid(row["id"]),
#             "target_url": row["target_url"],
#             "title": row["title"],
#             "text_excerpt": row["text_excerpt"],
#             "risk_level": row["risk_level"],
#             "risk_score": row["risk_score"],
#             "threat_indicators": row["threat_indicators"],
#             "content_hash": row["content_hash"],
#             "is_duplicate": row["is_duplicate"],
#             "alerts_triggered": row["alerts_triggered"] or [],
#             "created_at": row["created_at"].isoformat() if row["created_at"] else None,
#             "detected_at": row["detected_at"].isoformat() if row["detected_at"] else None,
#         }
#     }
# 
# @router.get("/monitoring/stats")
# async def get_monitoring_stats(
#     current_user: dict = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get monitoring statistics for current user"""
#     user_id_str = current_user.get("sub")
#     if not user_id_str:
#         raise HTTPException(status_code=401, detail="Authentication required")
# 
#     user_id = _get_user_uuid(user_id_str)
# 
#     try:
#         # Count duplicates
#         dup_result = await db.execute(
#             select(func.count(MonitoringResult.id)).where(
#                 MonitoringResult.user_id == user_id,
#                 MonitoringResult.is_duplicate == True
#             )
#         )
#         duplicate_count = dup_result.scalar() or 0
# 
#         # Count by risk level
#         high_risk_result = await db.execute(
#             select(func.count(MonitoringResult.id)).where(
#                 MonitoringResult.user_id == user_id,
#                 MonitoringResult.risk_level.in_(["high", "critical"])
#             )
#         )
#         high_risk_count = high_risk_result.scalar() or 0
# 
#         # Total results
#         total_result = await db.execute(
#             select(func.count(MonitoringResult.id)).where(
#                 MonitoringResult.user_id == user_id
#             )
#         )
#         total_count = total_result.scalar() or 0
# 
#         return {
#             "success": True,
#             "stats": {
#                 "total_results": total_count,
#                 "duplicate_results": duplicate_count,
#                 "high_risk_findings": high_risk_count,
#                 "unique_results": total_count - duplicate_count
#             }
#         }
# 
#     except Exception as e:
#         logger.error(f"[Monitoring] Stats failed: {e}")
#         raise HTTPException(status_code=500, detail="Failed to fetch stats")
# 



from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text
from app.database.database import get_db
from app.services.kafka_producer import KafkaProducer
from app.api.deps import get_current_user   # still imported — used by other endpoints
from app.models.alert import Alert
from app.models.monitoring_result import MonitoringResult
from app.services.crypto_utils import encrypt_credential
from app.services.scheduler import MonitoringScheduler
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["monitoring"])

# Global Kafka producer (reused across requests)
_kafka_producer: Optional[KafkaProducer] = None
_scheduler: Optional[MonitoringScheduler] = None

def set_scheduler(scheduler: MonitoringScheduler):
    """Set the global scheduler instance"""
    global _scheduler
    _scheduler = scheduler

async def get_kafka() -> KafkaProducer:
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducer()
        await _kafka_producer.connect()
    return _kafka_producer

def _get_user_uuid(user_id_str: str) -> uuid.UUID:
    try:
        if isinstance(user_id_str, uuid.UUID):
            return user_id_str
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id_str)


# ────────────────────────────────────────────────────────────────
#  These 6 endpoints are now PUBLIC (no authentication required)
# ────────────────────────────────────────────────────────────────

@router.post("/monitor/target")
async def setup_target_monitoring(
    title: str = Query(..., min_length=3, max_length=120),
    url: str = Query(..., min_length=10, pattern=r"^http://.*\.onion"),
    interval_hours: int = Query(6, ge=1, le=720),
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    login_path: Optional[str] = Query(None),
    username_selector: Optional[str] = Query(None),
    password_selector: Optional[str] = Query(None),
    submit_selector: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaProducer = Depends(get_kafka)
):
    """
    Setup continuous monitoring of a .onion URL — PUBLIC (no auth)
    """
    if (username and not password) or (password and not username):
        raise HTTPException(400, "Both username and password required for auth")

    # No user_id check — job is anonymous
    job_id = str(uuid.uuid4())

    encrypted_username = None
    encrypted_password = None
    
    if username and password:
        try:
            encrypted_username = encrypt_credential(username)
            encrypted_password = encrypt_credential(password)
        except Exception as e:
            logger.error(f"Credential encryption failed: {e}")
            raise HTTPException(500, "Failed to encrypt credentials")

    payload = {
        "job_id": job_id,
        "job_type": "monitor",
        "title": title.strip(),
        "target_url": url.strip(),
        "interval_hours": interval_hours,
        "user_id": None,  # no owner
        "auth_username": encrypted_username,
        "auth_password": encrypted_password,
        "login_path": login_path,
        "username_selector": username_selector or 'input[name="username"], input[id="username"]',
        "password_selector": password_selector or 'input[name="password"], input[id="password"]',
        "submit_selector": submit_selector or 'button[type="submit"], input[type="submit"]',
        "created_at": datetime.now(timezone.utc).isoformat(),
        "next_run_at": datetime.now(timezone.utc).isoformat()
    }

    await kafka.produce("monitor_jobs", payload)
    logger.info(f"[Monitor] Queued anonymous job {job_id} '{title}' for {url}")

    return {
        "success": True,
        "job_id": job_id,
        "title": title.strip(),
        "message": f"Monitoring started for '{title}' → {url}",
        "config": {
            "title": title.strip(),
            "url": url,
            "interval_hours": interval_hours,
            "requires_auth": bool(username),
            "status": "active"
        }
    }


@router.post("/alert/setup")
async def setup_alert(
    keyword: str = Query(..., min_length=2, max_length=100),
    risk_threshold: str = Query("medium", pattern="^(low|medium|high|critical)$"),
    notification_type: str = Query("email", pattern="^(email|webhook|slack)$"),
    notification_endpoint: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a real-time alert — PUBLIC (no auth)
    """
    if notification_type in ["email", "webhook", "slack"] and not notification_endpoint:
        raise HTTPException(400, f"{notification_type} requires notification_endpoint")

    alert = Alert(
        user_id=None,  # no owner
        keyword=keyword.strip().lower(),
        risk_level_threshold=risk_threshold,
        notification_type=notification_type,
        notification_endpoint=notification_endpoint.strip() if notification_endpoint else None,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    logger.info(f"[Alert] Created anonymous alert {alert.id} for '{keyword}'")

    return {
        "success": True,
        "alert_id": str(alert.id),
        "keyword": keyword,
        "risk_threshold": risk_threshold,
        "notification_type": notification_type,
        "status": "active",
        "created_at": alert.created_at.isoformat()
    }


@router.delete("/alert/{alert_id}")
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) an alert — PUBLIC (no auth)
    """
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(404, "Alert not found")

    alert.is_active = False
    if hasattr(alert, 'deactivated_at'):
        alert.deactivated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"[Alert] Deactivated alert {alert_id}")
    return {"success": True, "message": "Alert deactivated"}


@router.get("/monitoring/results")
async def get_monitoring_results(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring results — PUBLIC (no user filter)
    """
    try:
        count_result = await db.execute(select(func.count(MonitoringResult.id)))
        total = count_result.scalar() or 0

        result = await db.execute(
            select(
                MonitoringResult.id.label("id_raw"),
                MonitoringResult.target_url,
                MonitoringResult.title,
                MonitoringResult.risk_level,
                MonitoringResult.risk_score,
                MonitoringResult.is_duplicate,
                MonitoringResult.alerts_triggered,
                MonitoringResult.created_at,
                MonitoringResult.detected_at,
            )
            .order_by(MonitoringResult.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        rows = result.all()

        def safe_uuid(val):
            if val is None: return None
            if isinstance(val, uuid.UUID): return str(val)
            if isinstance(val, str):
                try: return str(uuid.UUID(val))
                except ValueError: return val
            return str(val)

        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "id": safe_uuid(row.id_raw),
                    "target_url": row.target_url,
                    "title": row.title,
                    "risk_level": row.risk_level,
                    "risk_score": row.risk_score,
                    "is_duplicate": row.is_duplicate,
                    "alerts_triggered": row.alerts_triggered or [],
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "detected_at": row.detected_at.isoformat() if row.detected_at else None,
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"[Monitoring] Get results failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch results")


@router.get("/monitoring/results/{result_id}")
async def get_monitoring_result_detail(
    result_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed monitoring result — PUBLIC
    """
    try:
        result = await db.execute(
            text("""
                SELECT 
                    id,
                    target_url,
                    title,
                    text_excerpt,
                    risk_level,
                    risk_score,
                    threat_indicators,
                    content_hash,
                    is_duplicate,
                    alerts_triggered,
                    created_at,
                    detected_at
                FROM monitoring_results
                WHERE id = :result_id
            """),
            {"result_id": result_id}
        )

        row = result.mappings().first()

        if not row:
            raise HTTPException(404, "Monitoring result not found")

        def safe_uuid(val):
            if val is None: return None
            if isinstance(val, uuid.UUID): return str(val)
            if isinstance(val, str):
                try: return str(uuid.UUID(val))
                except ValueError: return val
            return str(val)

        return {
            "success": True,
            "result": {
                "id": safe_uuid(row["id"]),
                "target_url": row["target_url"],
                "title": row["title"],
                "text_excerpt": row["text_excerpt"],
                "risk_level": row["risk_level"],
                "risk_score": row["risk_score"],
                "threat_indicators": row["threat_indicators"],
                "content_hash": row["content_hash"],
                "is_duplicate": row["is_duplicate"],
                "alerts_triggered": row["alerts_triggered"] or [],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "detected_at": row["detected_at"].isoformat() if row["detected_at"] else None,
            }
        }

    except Exception as e:
        logger.error(f"Get result detail failed: {e}")
        raise HTTPException(500, "Failed to fetch result detail")


@router.get("/monitoring/stats")
async def get_monitoring_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get global monitoring statistics — PUBLIC (no user filter)
    """
    try:
        # Count duplicates
        dup_result = await db.execute(
            select(func.count(MonitoringResult.id)).where(MonitoringResult.is_duplicate == True)
        )
        duplicate_count = dup_result.scalar() or 0

        # Count high/critical risk
        high_risk_result = await db.execute(
            select(func.count(MonitoringResult.id)).where(
                MonitoringResult.risk_level.in_(["high", "critical"])
            )
        )
        high_risk_count = high_risk_result.scalar() or 0

        # Total results
        total_result = await db.execute(select(func.count(MonitoringResult.id)))
        total_count = total_result.scalar() or 0

        return {
            "success": True,
            "stats": {
                "total_results": total_count,
                "duplicate_results": duplicate_count,
                "high_risk_findings": high_risk_count,
                "unique_results": total_count - duplicate_count
            }
        }

    except Exception as e:
        logger.error(f"[Monitoring] Stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")