from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UUID, Text, Enum as SQLEnum, Boolean, UniqueConstraint
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
    
    # Unique title per user (required)
    title = Column(String(120), nullable=False, index=True)
    
    # Target configuration
    target_url = Column(String(512), nullable=False, index=True)
    interval_hours = Column(Integer, default=6)  # Check every N hours
    
    auth_username_encrypted = Column(String(512), nullable=True)
    auth_password_encrypted = Column(String(512), nullable=True)
    login_path = Column(String(256), nullable=True)  # Optional custom login path
    username_selector = Column(String(256), nullable=True)  # Custom form selector
    password_selector = Column(String(256), nullable=True)  # Custom form selector
    submit_selector = Column(String(256), nullable=True)  # Custom submit button selector
    
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

    # Unique constraint: one user cannot have two jobs with the same title
    __table_args__ = (
        UniqueConstraint('user_id', 'title', name='uix_user_title'),
    )