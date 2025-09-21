from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
from app.models.user import User, UserSession, AuditLog
from app.schemas.auth import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.core.auth import PasswordManager, AuthenticationService
from app.core.config import settings

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        existing_user = db.query(User).filter(
            or_(User.email == user_data.email, User.username == user_data.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise ValueError("Email already registered")
            else:
                raise ValueError("Username already taken")
        
        hashed_password = PasswordManager.hash_password(user_data.password)
        
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=True,
            is_verified=False
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User created: {db_user.username} ({db_user.email})")
        return db_user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        
        if "password" in update_data:
            update_data["hashed_password"] = PasswordManager.hash_password(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User updated: {db_user.username}")
        return db_user
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return False
        
        db_user.is_active = False
        db.commit()
        
        logger.info(f"User deactivated: {db_user.username}")
        return True
    
    @staticmethod
    def get_users(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[User], int]:
        query = db.query(User)
        
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        total = query.count()
        
        order_column = getattr(User, order_by, User.created_at)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        users = query.offset(skip).limit(limit).all()
        
        return users, total
    
    @staticmethod
    def increment_failed_login_attempts(db: Session, user_id: int) -> None:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.failed_login_attempts += 1
            if db_user.failed_login_attempts >= settings.security.max_login_attempts:
                lockout_until = datetime.utcnow() + timedelta(minutes=settings.security.lockout_duration_minutes)
                db_user.locked_until = lockout_until
            db.commit()
    
    @staticmethod
    def reset_failed_login_attempts(db: Session, user_id: int) -> None:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.failed_login_attempts = 0
            db_user.locked_until = None
            db_user.last_login = datetime.utcnow()
            db.commit()


class SessionService:
    @staticmethod
    def create_session(
        db: Session, 
        user_id: int, 
        session_token: str, 
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        expires_at = datetime.utcnow() + timedelta(days=settings.security.refresh_token_expire_days)
        
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    @staticmethod
    def get_session_by_token(db: Session, session_token: str) -> Optional[UserSession]:
        return db.query(UserSession).filter(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        ).first()
    
    @staticmethod
    def invalidate_session(db: Session, session_token: str) -> bool:
        session = db.query(UserSession).filter(UserSession.session_token == session_token).first()
        if session:
            session.is_active = False
            db.commit()
            return True
        return False
    
    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_sessions)
        for session in expired_sessions:
            session.is_active = False
        
        db.commit()
        return count


class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        return audit_log
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[AuditLog], int]:
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        total = query.count()
        logs = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()
        
        return logs, total
