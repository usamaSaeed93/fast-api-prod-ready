from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import (
    UserCreate, UserResponse, UserUpdate, LoginRequest, Token,
    BackgroundJobCreate, BackgroundJobResponse, EmailRequest, HealthResponse
)
from app.auth import (
    authenticate_user, create_access_token, get_current_active_user,
    get_current_superuser
)
from app.services import UserService, BackgroundJobService
from app.background_jobs import publish_background_job
from app.email_service import email_service
from app.models import User
from datetime import datetime, timedelta
from app.config import settings

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    if UserService.get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if UserService.get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    db_user = UserService.create_user(db, user)
    
    # Send welcome email in background
    try:
        publish_background_job("send_email", {
            "to_email": user.email,
            "subject": "Welcome to FastAPI Demo!",
            "body": f"Welcome {user.username}! Thank you for registering.",
            "is_html": False
        })
    except Exception as e:
        # Log error but don't fail registration
        print(f"Failed to queue welcome email: {e}")
    
    return db_user


@router.post("/login", response_model=Token)
async def login_user(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return access token"""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    updated_user = UserService.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get list of users (admin only)"""
    users = UserService.get_users(db, skip=skip, limit=limit)
    return users


@router.post("/background-jobs", response_model=BackgroundJobResponse)
async def create_background_job(
    job_data: BackgroundJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new background job"""
    # Create job record in database
    db_job = BackgroundJobService.create_job(db, job_data)
    
    # Publish job to RabbitMQ
    try:
        job_id = publish_background_job(job_data.job_type, job_data.payload)
        # Update job record with the actual job_id from RabbitMQ
        db_job.job_id = job_id
        db.commit()
        db.refresh(db_job)
    except Exception as e:
        # Update job status to failed
        BackgroundJobService.update_job_status(db, db_job.job_id, "failed", error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background job: {e}"
        )
    
    return db_job


@router.get("/background-jobs", response_model=List[BackgroundJobResponse])
async def get_background_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of background jobs"""
    jobs = BackgroundJobService.get_jobs(db, skip=skip, limit=limit)
    return jobs


@router.get("/background-jobs/{job_id}", response_model=BackgroundJobResponse)
async def get_background_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific background job"""
    job = BackgroundJobService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job


@router.post("/send-email", status_code=status.HTTP_202_ACCEPTED)
async def send_email(
    email_request: EmailRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Send an email (queued as background job)"""
    try:
        job_id = publish_background_job("send_email", {
            "to_email": email_request.to_email,
            "subject": email_request.subject,
            "body": email_request.body,
            "is_html": email_request.is_html
        })
        return {"message": "Email queued for sending", "job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue email: {e}"
        )


@router.post("/send-notification", status_code=status.HTTP_202_ACCEPTED)
async def send_notification(
    message: str,
    current_user: User = Depends(get_current_active_user)
):
    """Send a notification (queued as background job)"""
    try:
        job_id = publish_background_job("notification", {
            "message": message,
            "user_id": current_user.id
        })
        return {"message": "Notification queued", "job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue notification: {e}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        services={
            "database": "connected",
            "rabbitmq": "connected",
            "email": "configured" if settings.smtp_username else "not_configured"
        }
    )
