from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_active_user
from app.models.user import User
from app.schemas.common import HealthResponse, MetricsResponse, SystemInfo
from app.core.monitoring import get_health_status, get_metrics
from app.core.config import settings
import sys
import fastapi

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return get_health_status()


@router.get("/metrics")
async def get_prometheus_metrics():
    from fastapi.responses import Response
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain")


@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    return SystemInfo(
        version=settings.api.version,
        environment=settings.environment.value,
        python_version=sys.version,
        fastapi_version=fastapi.__version__,
        database_url=settings.database.url,
        redis_url=settings.cache.url,
        rabbitmq_url=settings.message_queue.url
    )
