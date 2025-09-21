from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class JobType(str, Enum):
    EMAIL = "send_email"
    NOTIFICATION = "notification"
    DATA_PROCESSING = "data_processing"
    CLEANUP = "cleanup"
    REPORT_GENERATION = "report_generation"
    FILE_PROCESSING = "file_processing"


class BackgroundJobCreate(BaseModel):
    job_type: JobType
    payload: Optional[Dict[str, Any]] = None
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = Field(default=3, ge=0, le=10)


class BackgroundJobResponse(BaseModel):
    id: int
    job_id: str
    job_type: str
    status: str
    priority: int
    payload: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    created_by: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BackgroundJobListResponse(BaseModel):
    jobs: List[BackgroundJobResponse]
    total: int
    page: int
    size: int
    pages: int


class JobStatusUpdate(BaseModel):
    status: JobStatus
    result: Optional[str] = None
    error_message: Optional[str] = None


class EmailRequest(BaseModel):
    to_email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    is_html: bool = False
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    @validator('cc', 'bcc')
    def validate_email_lists(cls, v):
        if v:
            for email in v:
                if not email or '@' not in email:
                    raise ValueError(f'Invalid email address: {email}')
        return v


class NotificationRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    notification_type: str = Field(default="info")
    channels: List[str] = Field(default=["email"])
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class DataProcessingRequest(BaseModel):
    data_source: str
    processing_type: str
    parameters: Optional[Dict[str, Any]] = None
    output_format: str = "json"


class CleanupRequest(BaseModel):
    cleanup_type: str
    older_than_days: int = Field(default=30, ge=1, le=365)
    dry_run: bool = False
