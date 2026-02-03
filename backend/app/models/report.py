# app/models/report.py
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UUID, Text, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.orm import declarative_base
import uuid
import enum

Base = declarative_base()


class ReportType(str, enum.Enum):
    COMPREHENSIVE = "comprehensive"
    EXECUTIVE     = "executive"
    TECHNICAL     = "technical"


class ReportStatus(str, enum.Enum):
    PENDING     = "pending"
    GENERATING  = "generating"
    COMPLETED   = "completed"
    FAILED      = "failed"


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    report_type = Column(SQLEnum(ReportType), nullable=False)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING, nullable=False)

    # Filters used when generating the report
    filters = Column(JSON, nullable=True)

    # Stats (populated after generation)
    threats_count    = Column(Integer, default=0, nullable=False)
    indicators_count = Column(Integer, default=0, nullable=False)

    # File information
    file_path    = Column(String(512), nullable=True, index=True)
    file_size_mb = Column(String(20), nullable=True)           # "2.4" or "0.8"

    # Timestamps
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at   = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Sharing
    share_token      = Column(String(64), unique=True, nullable=True, index=True)
    share_expires_at = Column(DateTime, nullable=True)
    is_publicly_shared = Column(Boolean, default=False, nullable=False)

    progress = Column(Integer, default=0, nullable=False)
