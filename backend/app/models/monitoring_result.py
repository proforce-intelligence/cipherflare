from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UUID, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class MonitoringResult(Base):
    __tablename__ = "monitoring_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Source tracking
    target_url = Column(String(512), nullable=False, index=True)
    
    # Content data
    title = Column(String(512), nullable=True)
    text_excerpt = Column(Text, nullable=True)
    risk_level = Column(String(50), nullable=True)  # low, medium, high, critical
    risk_score = Column(Float, default=0.0)
    threat_indicators = Column(JSON, nullable=True)  # List of threat indicators
    
    # Deduplication tracking
    content_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash of content
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_of_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to original
    
    # Monitoring job tracking
    monitor_job_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Link to monitoring job
    
    # Alert triggering
    alerts_triggered = Column(JSON, nullable=True)  # List of alert IDs triggered
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    detected_at = Column(DateTime, nullable=True)  # When change was detected on page
