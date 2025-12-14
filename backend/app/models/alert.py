from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UUID, Text, Float, Boolean
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Alert trigger
    keyword = Column(String(255), nullable=False, index=True)
    risk_level_threshold = Column(String(50), default="medium")  # low, medium, high, critical
    
    # Configuration
    is_active = Column(Boolean, default=True)
    notification_type = Column(String(50), default="email")  # email, webhook
    notification_endpoint = Column(String(512), nullable=True)  # Email or webhook URL
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
