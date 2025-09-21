from sqlalchemy.orm import Session
from app.models import User, BackgroundJob
from app.schemas import UserCreate, UserUpdate, BackgroundJobCreate
from app.auth import get_password_hash
from typing import List, Optional
import uuid
import json


class UserService:
    """Service for user operations"""
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user information"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users"""
        return db.query(User).offset(skip).limit(limit).all()


class BackgroundJobService:
    """Service for background job operations"""
    
    @staticmethod
    def create_job(db: Session, job_data: BackgroundJobCreate) -> BackgroundJob:
        """Create a new background job"""
        job_id = str(uuid.uuid4())
        payload_json = json.dumps(job_data.payload) if job_data.payload else None
        
        db_job = BackgroundJob(
            job_id=job_id,
            job_type=job_data.job_type,
            payload=payload_json
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job
    
    @staticmethod
    def get_job_by_id(db: Session, job_id: str) -> Optional[BackgroundJob]:
        """Get job by job_id"""
        return db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
    
    @staticmethod
    def update_job_status(
        db: Session, 
        job_id: str, 
        status: str, 
        result: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[BackgroundJob]:
        """Update job status"""
        db_job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
        if not db_job:
            return None
        
        db_job.status = status
        if result:
            db_job.result = result
        if error_message:
            db_job.error_message = error_message
        
        db.commit()
        db.refresh(db_job)
        return db_job
    
    @staticmethod
    def get_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[BackgroundJob]:
        """Get list of background jobs"""
        return db.query(BackgroundJob).offset(skip).limit(limit).all()
