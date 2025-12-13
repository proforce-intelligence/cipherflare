from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

class JobType(str, Enum):
    AD_HOC = "ad_hoc"
    MONITOR = "monitor"

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobCreate(BaseModel):
    job_type: JobType
    keyword: Optional[str] = None
    target_url: Optional[str] = None
    max_results: Optional[int] = Field(default=None, le=10000)
    payload: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    id: UUID
    job_type: JobStatus
    keyword: Optional[str]
    target_url: Optional[str]
    findings_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
