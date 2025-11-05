from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database.database import Base

class DarkWebSearchRequest(BaseModel):
    keyword: str
    max_results: int = 10
    depth: int = 0
    create_case: bool = True

class DarkWebMonitorRequest(BaseModel):
    keywords: List[str]
    monitor_name: str
    alert_threshold: int = 1

class DarkWebResult(BaseModel):
    url: str
    title: Optional[str]
    description: Optional[str]
    risk_level: str
    entities: dict
    keywords_found: List[str]
    relevance_score: float
    scraped_at: str
    screenshot_file: Optional[str]
    text_file: Optional[str]
    # + your meta fields

# SQL Models (your existing)
class DarkWebMonitor(Base):
    __tablename__ = "dark_web_monitors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String)
    keywords = Column(JSON)
    alert_threshold = Column(Integer)
    status = Column(String, default="active")
    next_scan = Column(DateTime)
    last_scan = Column(DateTime)
    alerts_count = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# Similarly for DarkWebAlert, DarkWebFinding, etc.