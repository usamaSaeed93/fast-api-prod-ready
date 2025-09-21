import structlog
import logging
import sys
from typing import Any, Dict
from app.core.config import settings


def configure_logging():
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.monitoring.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.monitoring.log_level.value),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


class LoggerMixin:
    @property
    def logger(self) -> structlog.BoundLogger:
        return get_logger(self.__class__.__name__)


def log_function_call(func: callable) -> callable:
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(
            "Function called",
            function=func.__name__,
            module=func.__module__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        try:
            result = func(*args, **kwargs)
            logger.info(
                "Function completed",
                function=func.__name__,
                success=True
            )
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                success=False,
                exc_info=True
            )
            raise
    
    return wrapper


def log_database_operation(operation: str, table: str, **kwargs):
    logger = get_logger("database")
    logger.info(
        "Database operation",
        operation=operation,
        table=table,
        **kwargs
    )


def log_api_request(method: str, path: str, status_code: int, **kwargs):
    logger = get_logger("api")
    logger.info(
        "API request",
        method=method,
        path=path,
        status_code=status_code,
        **kwargs
    )


def log_background_job(job_id: str, job_type: str, status: str, **kwargs):
    logger = get_logger("background_job")
    logger.info(
        "Background job",
        job_id=job_id,
        job_type=job_type,
        status=status,
        **kwargs
    )


def log_security_event(event_type: str, user_id: int = None, ip_address: str = None, **kwargs):
    logger = get_logger("security")
    logger.warning(
        "Security event",
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        **kwargs
    )
