from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, index=True, nullable=False)
    job_type = Column(String(100), nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    payload = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    creator = relationship("User", backref="created_jobs")
    
    __table_args__ = (
        Index('ix_background_jobs_status', 'status'),
        Index('ix_background_jobs_type_status', 'job_type', 'status'),
        Index('ix_background_jobs_created_by', 'created_by'),
        Index('ix_background_jobs_priority', 'priority'),
    )
