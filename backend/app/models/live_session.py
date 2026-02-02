"""
Live Mirror Session Model - Tracks active live browsing sessions
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, Boolean, Integer
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class LiveSession(Base):
    __tablename__ = "live_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Session configuration
    target_url = Column(String(512), nullable=False)
    javascript_enabled = Column(Boolean, default=False)
    
    # Session state
    is_active = Column(Boolean, default=True, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Statistics
    page_views = Column(Integer, default=0)
    screenshots_taken = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Session timeout
