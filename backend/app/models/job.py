from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UUID, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
import uuid
import enum

Base = declarative_base()

class JobType(str, enum.Enum):
    AD_HOC = "ad_hoc"
    MONITOR = "monitor"

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Can be null for unauthenticated requests
    job_type = Column(SQLEnum(JobType), nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    
    # Job metadata
    keyword = Column(String(255), nullable=True)  # For ad_hoc searches
    target_url = Column(String(512), nullable=True)  # For monitor jobs
    max_results = Column(Integer, default=50)
    
    # Payload (JSON string for flexibility)
    payload = Column(Text, nullable=True)  # Stores credentials, config, etc.
    
    # Results
    findings_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
