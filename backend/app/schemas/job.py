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
    max_results: int = Field(default=50, le=200)
    payload: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    id: UUID
    job_type: JobType
    status: JobStatus
    keyword: Optional[str]
    target_url: Optional[str]
    findings_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
