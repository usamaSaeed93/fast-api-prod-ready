from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    echo: bool = Field(default=False, env="DATABASE_ECHO")


class SecuritySettings(BaseSettings):
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15, env="LOCKOUT_DURATION_MINUTES")


class MessageQueueSettings(BaseSettings):
    url: str = Field(..., env="RABBITMQ_URL")
    exchange: str = Field(default="fastapi_demo", env="RABBITMQ_EXCHANGE")
    queue_prefix: str = Field(default="app", env="RABBITMQ_QUEUE_PREFIX")
    max_retries: int = Field(default=3, env="RABBITMQ_MAX_RETRIES")
    retry_delay: int = Field(default=5, env="RABBITMQ_RETRY_DELAY")
    prefetch_count: int = Field(default=1, env="RABBITMQ_PREFETCH_COUNT")


class CacheSettings(BaseSettings):
    url: str = Field(..., env="REDIS_URL")
    key_prefix: str = Field(default="fastapi_demo:", env="REDIS_KEY_PREFIX")
    default_ttl: int = Field(default=3600, env="REDIS_DEFAULT_TTL")
    max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")


class EmailSettings(BaseSettings):
    smtp_server: str = Field(default="smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    from_email: str = Field(default="noreply@example.com", env="SMTP_FROM_EMAIL")
    use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    timeout: int = Field(default=30, env="SMTP_TIMEOUT")


class MonitoringSettings(BaseSettings):
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")
    tracing_endpoint: Optional[str] = Field(default=None, env="TRACING_ENDPOINT")
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")


class APISettings(BaseSettings):
    title: str = Field(default="FastAPI Enterprise Demo", env="API_TITLE")
    version: str = Field(default="1.0.0", env="API_VERSION")
    description: str = Field(default="Enterprise-grade FastAPI application", env="API_DESCRIPTION")
    docs_url: str = Field(default="/docs", env="API_DOCS_URL")
    redoc_url: str = Field(default="/redoc", env="API_REDOC_URL")
    openapi_url: str = Field(default="/openapi.json", env="API_OPENAPI_URL")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")


class Settings(BaseSettings):
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    database: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()
    message_queue: MessageQueueSettings = MessageQueueSettings()
    cache: CacheSettings = CacheSettings()
    email: EmailSettings = EmailSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    api: APISettings = APISettings()
    
    @validator("debug")
    def validate_debug(cls, v, values):
        if "environment" in values and values["environment"] == Environment.PRODUCTION:
            return False
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False


settings = Settings()
