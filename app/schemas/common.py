from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthResponse(BaseModel):
    status: HealthStatus
    timestamp: datetime
    version: str
    environment: str
    services: Dict[str, ServiceStatus]
    uptime_seconds: float
    memory_usage: Optional[Dict[str, Any]] = None
    database_status: Optional[Dict[str, Any]] = None
    cache_status: Optional[Dict[str, Any]] = None
    message_queue_status: Optional[Dict[str, Any]] = None


class MetricsResponse(BaseModel):
    timestamp: datetime
    metrics: Dict[str, Any]


class SystemInfo(BaseModel):
    version: str
    environment: str
    python_version: str
    fastapi_version: str
    database_url: str
    redis_url: str
    rabbitmq_url: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int
    timestamp: datetime
    request_id: Optional[str] = None


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(PaginatedResponse):
    logs: List[AuditLogResponse]
