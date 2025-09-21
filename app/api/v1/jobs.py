from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_superuser
from app.models.user import User
from app.models.job import BackgroundJob
from app.schemas.job import (
    BackgroundJobCreate, BackgroundJobResponse, BackgroundJobListResponse,
    EmailRequest, NotificationRequest, DataProcessingRequest, CleanupRequest
)
from app.schemas.common import PaginationParams
from app.services.job_service import BackgroundJobService
from app.core.message_queue import JobPublisher
from app.core.logging import log_background_job, log_api_request
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("/jobs", response_model=BackgroundJobResponse, status_code=status.HTTP_201_CREATED)
async def create_background_job(
    job_data: BackgroundJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        db_job = BackgroundJobService.create_job(db, job_data, current_user.id)
        
        success = JobPublisher.publish_job(
            job_type=job_data.job_type.value,
            payload=job_data.payload or {},
            priority=job_data.priority.value
        )
        
        if not success:
            BackgroundJobService.update_job_status(
                db, db_job.job_id, JobStatusUpdate(status="failed", error_message="Failed to queue job")
            )
            raise HTTPException(status_code=500, detail="Failed to queue background job")
        
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="background_job_created",
            resource_type="background_job",
            resource_id=db_job.job_id,
            details=f"Type: {job_data.job_type.value}, Priority: {job_data.priority.value}"
        )
        
        log_background_job(db_job.job_id, job_data.job_type.value, "created")
        
        return db_job
        
    except Exception as e:
        log_background_job("unknown", job_data.job_type.value, "creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create background job: {e}")


@router.get("/jobs", response_model=BackgroundJobListResponse)
async def get_background_jobs(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    jobs, total = BackgroundJobService.get_jobs(
        db=db,
        skip=pagination.offset,
        limit=pagination.size,
        status=status,
        job_type=job_type,
        created_by=current_user.id if not current_user.is_superuser else None
    )
    
    pages = (total + pagination.size - 1) // pagination.size
    
    return BackgroundJobListResponse(
        jobs=jobs,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages
    )


@router.get("/jobs/{job_id}", response_model=BackgroundJobResponse)
async def get_background_job(
    job_id: str = Path(..., min_length=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    job = BackgroundJobService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not current_user.is_superuser and job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return job


@router.get("/jobs/statistics")
async def get_job_statistics(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    stats = BackgroundJobService.get_job_statistics(db)
    return stats


@router.post("/send-email", status_code=status.HTTP_202_ACCEPTED)
async def send_email(
    email_request: EmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        job_data = BackgroundJobCreate(
            job_type="send_email",
            payload={
                "to_email": email_request.to_email,
                "subject": email_request.subject,
                "body": email_request.body,
                "is_html": email_request.is_html,
                "cc": email_request.cc,
                "bcc": email_request.bcc,
                "attachments": email_request.attachments
            }
        )
        
        db_job = BackgroundJobService.create_job(db, job_data, current_user.id)
        
        success = JobPublisher.publish_job(
            job_type="send_email",
            payload=job_data.payload,
            priority=1
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue email")
        
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="email_queued",
            resource_type="email",
            resource_id=db_job.job_id,
            details=f"To: {email_request.to_email}, Subject: {email_request.subject}"
        )
        
        return {"message": "Email queued for sending", "job_id": db_job.job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {e}")


@router.post("/send-notification", status_code=status.HTTP_202_ACCEPTED)
async def send_notification(
    notification_request: NotificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        job_data = BackgroundJobCreate(
            job_type="notification",
            payload={
                "message": notification_request.message,
                "notification_type": notification_request.notification_type,
                "channels": notification_request.channels,
                "user_id": notification_request.user_id or current_user.id,
                "metadata": notification_request.metadata
            }
        )
        
        db_job = BackgroundJobService.create_job(db, job_data, current_user.id)
        
        success = JobPublisher.publish_job(
            job_type="notification",
            payload=job_data.payload,
            priority=1
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue notification")
        
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="notification_queued",
            resource_type="notification",
            resource_id=db_job.job_id,
            details=f"Type: {notification_request.notification_type}"
        )
        
        return {"message": "Notification queued", "job_id": db_job.job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue notification: {e}")


@router.post("/process-data", status_code=status.HTTP_202_ACCEPTED)
async def process_data(
    data_request: DataProcessingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        job_data = BackgroundJobCreate(
            job_type="data_processing",
            payload={
                "data_source": data_request.data_source,
                "processing_type": data_request.processing_type,
                "parameters": data_request.parameters,
                "output_format": data_request.output_format
            }
        )
        
        db_job = BackgroundJobService.create_job(db, job_data, current_user.id)
        
        success = JobPublisher.publish_job(
            job_type="data_processing",
            payload=job_data.payload,
            priority=0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue data processing")
        
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="data_processing_queued",
            resource_type="data_processing",
            resource_id=db_job.job_id,
            details=f"Source: {data_request.data_source}, Type: {data_request.processing_type}"
        )
        
        return {"message": "Data processing queued", "job_id": db_job.job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue data processing: {e}")


@router.post("/cleanup", status_code=status.HTTP_202_ACCEPTED)
async def cleanup_system(
    cleanup_request: CleanupRequest,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    try:
        job_data = BackgroundJobCreate(
            job_type="cleanup",
            payload={
                "cleanup_type": cleanup_request.cleanup_type,
                "older_than_days": cleanup_request.older_than_days,
                "dry_run": cleanup_request.dry_run
            }
        )
        
        db_job = BackgroundJobService.create_job(db, job_data, current_user.id)
        
        success = JobPublisher.publish_job(
            job_type="cleanup",
            payload=job_data.payload,
            priority=0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue cleanup")
        
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="cleanup_queued",
            resource_type="cleanup",
            resource_id=db_job.job_id,
            details=f"Type: {cleanup_request.cleanup_type}, Days: {cleanup_request.older_than_days}"
        )
        
        return {"message": "Cleanup queued", "job_id": db_job.job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue cleanup: {e}")
