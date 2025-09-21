from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid
import json
import logging
from app.models.job import BackgroundJob
from app.schemas.job import BackgroundJobCreate, JobStatusUpdate, JobStatus, JobPriority
from app.core.config import settings

logger = logging.getLogger(__name__)


class BackgroundJobService:
    @staticmethod
    def create_job(db: Session, job_data: BackgroundJobCreate, created_by: Optional[int] = None) -> BackgroundJob:
        job_id = str(uuid.uuid4())
        payload_json = json.dumps(job_data.payload) if job_data.payload else None
        
        db_job = BackgroundJob(
            job_id=job_id,
            job_type=job_data.job_type.value,
            payload=payload_json,
            priority=job_data.priority.value,
            max_retries=job_data.max_retries,
            created_by=created_by,
            status=JobStatus.PENDING.value
        )
        
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        
        logger.info(f"Background job created: {job_id} ({job_data.job_type.value})")
        return db_job
    
    @staticmethod
    def get_job_by_id(db: Session, job_id: str) -> Optional[BackgroundJob]:
        return db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
    
    @staticmethod
    def get_job_by_db_id(db: Session, db_id: int) -> Optional[BackgroundJob]:
        return db.query(BackgroundJob).filter(BackgroundJob.id == db_id).first()
    
    @staticmethod
    def update_job_status(
        db: Session,
        job_id: str,
        status_update: JobStatusUpdate
    ) -> Optional[BackgroundJob]:
        db_job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
        if not db_job:
            return None
        
        db_job.status = status_update.status.value
        
        if status_update.result:
            db_job.result = status_update.result
        
        if status_update.error_message:
            db_job.error_message = status_update.error_message
        
        if status_update.status == JobStatus.PROCESSING:
            db_job.started_at = datetime.utcnow()
        elif status_update.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            db_job.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_job)
        
        logger.info(f"Job status updated: {job_id} -> {status_update.status.value}")
        return db_job
    
    @staticmethod
    def increment_retry_count(db: Session, job_id: str) -> Optional[BackgroundJob]:
        db_job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
        if not db_job:
            return None
        
        db_job.retry_count += 1
        db_job.status = JobStatus.RETRYING.value
        
        db.commit()
        db.refresh(db_job)
        
        logger.info(f"Job retry count incremented: {job_id} -> {db_job.retry_count}")
        return db_job
    
    @staticmethod
    def get_jobs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[JobStatus] = None,
        job_type: Optional[str] = None,
        created_by: Optional[int] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[BackgroundJob], int]:
        query = db.query(BackgroundJob)
        
        if status:
            query = query.filter(BackgroundJob.status == status.value)
        
        if job_type:
            query = query.filter(BackgroundJob.job_type == job_type)
        
        if created_by:
            query = query.filter(BackgroundJob.created_by == created_by)
        
        total = query.count()
        
        order_column = getattr(BackgroundJob, order_by, BackgroundJob.created_at)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        jobs = query.offset(skip).limit(limit).all()
        
        return jobs, total
    
    @staticmethod
    def get_pending_jobs(db: Session, limit: int = 10) -> List[BackgroundJob]:
        return db.query(BackgroundJob).filter(
            BackgroundJob.status == JobStatus.PENDING.value
        ).order_by(
            desc(BackgroundJob.priority),
            asc(BackgroundJob.created_at)
        ).limit(limit).all()
    
    @staticmethod
    def get_failed_jobs_for_retry(db: Session, limit: int = 10) -> List[BackgroundJob]:
        return db.query(BackgroundJob).filter(
            and_(
                BackgroundJob.status == JobStatus.FAILED.value,
                BackgroundJob.retry_count < BackgroundJob.max_retries
            )
        ).order_by(
            desc(BackgroundJob.priority),
            asc(BackgroundJob.created_at)
        ).limit(limit).all()
    
    @staticmethod
    def cleanup_old_jobs(db: Session, older_than_days: int = 30) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        old_jobs = db.query(BackgroundJob).filter(
            and_(
                BackgroundJob.created_at < cutoff_date,
                BackgroundJob.status.in_([
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value
                ])
            )
        ).all()
        
        count = len(old_jobs)
        for job in old_jobs:
            db.delete(job)
        
        db.commit()
        
        logger.info(f"Cleaned up {count} old background jobs")
        return count
    
    @staticmethod
    def get_job_statistics(db: Session) -> Dict[str, Any]:
        total_jobs = db.query(BackgroundJob).count()
        
        status_counts = {}
        for status in JobStatus:
            count = db.query(BackgroundJob).filter(BackgroundJob.status == status.value).count()
            status_counts[status.value] = count
        
        type_counts = {}
        job_types = db.query(BackgroundJob.job_type).distinct().all()
        for job_type_tuple in job_types:
            job_type = job_type_tuple[0]
            count = db.query(BackgroundJob).filter(BackgroundJob.job_type == job_type).count()
            type_counts[job_type] = count
        
        return {
            "total_jobs": total_jobs,
            "status_counts": status_counts,
            "type_counts": type_counts
        }
