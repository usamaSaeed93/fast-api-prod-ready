import time
import uuid
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from app.core.config import settings
from app.services.audit_service import AuditService
from app.core.database import get_db_context

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"Request processed",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.environment.value == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        client_requests = self.clients[client_ip]
        
        client_requests[:] = [req_time for req_time in client_requests if current_time - req_time < self.period]
        
        if len(client_requests) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": self.period}
            )
        
        client_requests.append(current_time)
        
        response = await call_next(request)
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        if request.url.path.startswith("/api/"):
            try:
                with get_db_context() as db:
                    AuditService.log_action(
                        db=db,
                        user_id=getattr(request.state, "user_id", None),
                        action=f"{request.method} {request.url.path}",
                        resource_type="api_endpoint",
                        resource_id=request.url.path,
                        details=f"Status: {response.status_code}",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
            except Exception as e:
                logger.error(f"Failed to log audit: {e}")
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else None,
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": time.time()
                }
            )
