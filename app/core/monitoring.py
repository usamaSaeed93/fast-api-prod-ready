import time
import psutil
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from app.core.config import settings
from app.core.database import get_db_context
from app.core.cache import cache_manager
from app.services.job_service import BackgroundJobService
from app.models.job import JobStatus

logger = logging.getLogger(__name__)


REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

BACKGROUND_JOBS_TOTAL = Counter(
    'background_jobs_total',
    'Total background jobs',
    ['job_type', 'status']
)

BACKGROUND_JOBS_ACTIVE = Gauge(
    'background_jobs_active',
    'Number of active background jobs'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['operation']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['operation']
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)


class MetricsCollector:
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration: float):
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_background_job(job_type: str, status: str):
        BACKGROUND_JOBS_TOTAL.labels(job_type=job_type, status=status).inc()
    
    @staticmethod
    def record_cache_operation(operation: str, hit: bool):
        if hit:
            CACHE_HITS.labels(operation=operation).inc()
        else:
            CACHE_MISSES.labels(operation=operation).inc()
    
    @staticmethod
    def update_system_metrics():
        try:
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.used)
            SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    @staticmethod
    def update_background_job_metrics():
        try:
            with get_db_context() as db:
                active_jobs = BackgroundJobService.get_jobs(
                    db, status=JobStatus.PROCESSING, limit=1000
                )[0]
                BACKGROUND_JOBS_ACTIVE.set(len(active_jobs))
        except Exception as e:
            logger.error(f"Failed to update background job metrics: {e}")


class HealthChecker:
    @staticmethod
    def check_database() -> Dict[str, Any]:
        try:
            with get_db_context() as db:
                db.execute("SELECT 1")
                return {"status": "healthy", "response_time_ms": 0}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    @staticmethod
    def check_cache() -> Dict[str, Any]:
        try:
            is_healthy = cache_manager.health_check()
            return {"status": "healthy" if is_healthy else "unhealthy"}
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    @staticmethod
    def check_message_queue() -> Dict[str, Any]:
        try:
            from app.core.message_queue import message_queue_manager
            is_healthy = message_queue_manager.health_check()
            return {"status": "healthy" if is_healthy else "unhealthy"}
        except Exception as e:
            logger.error(f"Message queue health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percentage": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percentage": (disk.used / disk.total) * 100
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "usage_percent": psutil.cpu_percent(interval=1)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}


class MonitoringMiddleware:
    def __init__(self, app):
        self.app = app
        self.start_time = time.time()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            start_time = time.time()
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    duration = time.time() - start_time
                    MetricsCollector.record_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=message["status"],
                        duration=duration
                    )
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def get_metrics():
    MetricsCollector.update_system_metrics()
    MetricsCollector.update_background_job_metrics()
    return generate_latest()


def get_health_status() -> Dict[str, Any]:
    start_time = time.time()
    
    database_status = HealthChecker.check_database()
    cache_status = HealthChecker.check_cache()
    message_queue_status = HealthChecker.check_message_queue()
    system_info = HealthChecker.get_system_info()
    
    overall_status = "healthy"
    if any(status["status"] != "healthy" for status in [database_status, cache_status, message_queue_status]):
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.api.version,
        "environment": settings.environment.value,
        "uptime_seconds": time.time() - start_time,
        "services": {
            "database": database_status,
            "cache": cache_status,
            "message_queue": message_queue_status
        },
        "system": system_info
    }
