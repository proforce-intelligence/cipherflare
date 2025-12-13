from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UUID, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import declarative_base
import uuid
import enum

Base = declarative_base()

class MonitoringJobStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class MonitoringJob(Base):
    __tablename__ = "monitoring_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Target configuration
    target_url = Column(String(512), nullable=False, index=True)
    interval_hours = Column(Integer, default=6)  # Check every N hours
    
    # Status tracking
    status = Column(SQLEnum(MonitoringJobStatus), default=MonitoringJobStatus.ACTIVE, nullable=False, index=True)
    
    # Scheduling
    next_run_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True)
    
    # Statistics
    total_checks = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    alerts_triggered = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
