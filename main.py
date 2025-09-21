from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import logging
import time
from datetime import datetime

from app.core.config import settings
from app.core.database import create_tables
from app.core.logging import configure_logging, get_logger
from app.core.monitoring import MonitoringMiddleware
from app.middleware.security import (
    RequestIDMiddleware, TimingMiddleware, SecurityHeadersMiddleware,
    RateLimitMiddleware, AuditMiddleware, ErrorHandlingMiddleware
)
from app.api.v1 import auth, jobs, system

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting FastAPI application", version=settings.api.version)
    
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise
    
    yield
    
    logger.info("Shutting down FastAPI application")


app = FastAPI(
    title=settings.api.title,
    version=settings.api.version,
    description=settings.api.description,
    docs_url=settings.api.docs_url,
    redoc_url=settings.api.redoc_url,
    openapi_url=settings.api.openapi_url,
    lifespan=lifespan
)

app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)

if settings.environment.value != "production":
    app.add_middleware(RateLimitMiddleware, calls=1000, period=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_allow_credentials,
    allow_methods=settings.api.cors_allow_methods,
    allow_headers=settings.api.cors_allow_headers,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.environment.value != "production" else ["localhost", "127.0.0.1"]
)

if settings.monitoring.enable_metrics:
    app.add_middleware(MonitoringMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Background Jobs"])
app.include_router(system.router, prefix="/api/v1", tags=["System"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method,
        request_id=getattr(request.state, "request_id", None)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        exception=str(exc),
        url=str(request.url),
        method=request.method,
        request_id=getattr(request.state, "request_id", None),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to FastAPI Enterprise Demo",
        "version": settings.api.version,
        "environment": settings.environment.value,
        "docs": settings.api.docs_url,
        "redoc": settings.api.redoc_url,
        "health": "/api/v1/health"
    }


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.api.title,
        version=settings.api.version,
        description=settings.api.description,
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
        log_level=settings.monitoring.log_level.value.lower()
    )