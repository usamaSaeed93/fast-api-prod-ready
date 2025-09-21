from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_superuser
from app.models.user import User
from app.schemas.auth import (
    UserCreate, UserResponse, UserUpdate, UserListResponse,
    LoginRequest, TokenResponse, PasswordChangeRequest, RefreshTokenRequest
)
from app.schemas.common import PaginationParams, PaginatedResponse
from app.services.user_service import UserService, SessionService, AuditService
from app.core.auth import AuthenticationService, TokenManager
from app.core.logging import log_api_request, log_security_event

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    try:
        db_user = UserService.create_user(db, user_data)
        
        AuditService.log_action(
            db=db,
            user_id=db_user.id,
            action="user_registered",
            resource_type="user",
            resource_id=str(db_user.id),
            details=f"Email: {db_user.email}"
        )
        
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    user = AuthenticationService.authenticate_user(
        db, login_data.username, login_data.password
    )
    
    if not user:
        log_security_event(
            "login_failed",
            ip_address=request.client.host if request.client else None,
            details=f"Username: {login_data.username}"
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=423,
            detail="Account is temporarily locked due to too many failed login attempts"
        )
    
    tokens = AuthenticationService.create_tokens(user)
    
    SessionService.create_session(
        db=db,
        user_id=user.id,
        session_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    UserService.reset_failed_login_attempts(db, user.id)
    
    AuditService.log_action(
        db=db,
        user_id=user.id,
        action="user_login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    token_data = TokenManager.verify_token(refresh_data.refresh_token)
    
    if not token_data or token_data.token_type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = AuthenticationService.get_user_by_username(db, token_data.username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    tokens = AuthenticationService.create_tokens(user)
    
    return tokens


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="user_logout",
        resource_type="user",
        resource_id=str(current_user.id)
    )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    updated_user = UserService.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="user_updated",
        resource_type="user",
        resource_id=str(current_user.id)
    )
    
    return updated_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not PasswordManager.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    updated_user = UserService.update_user(
        db, 
        current_user.id, 
        UserUpdate(password=password_data.new_password)
    )
    
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="password_changed",
        resource_type="user",
        resource_id=str(current_user.id)
    )
    
    return {"message": "Password changed successfully"}


@router.get("/users", response_model=UserListResponse)
async def get_users(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    users, total = UserService.get_users(
        db=db,
        skip=pagination.offset,
        limit=pagination.size,
        search=search,
        is_active=is_active
    )
    
    pages = (total + pagination.size - 1) // pagination.size
    
    return UserListResponse(
        users=users,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int = Path(..., gt=0),
    user_update: UserUpdate = None,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = UserService.update_user(db, user_id, user_update)
    
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="user_updated_by_admin",
        resource_type="user",
        resource_id=str(user_id),
        details=f"Updated by admin: {current_user.username}"
    )
    
    return updated_user


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    success = UserService.deactivate_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="user_deactivated",
        resource_type="user",
        resource_id=str(user_id),
        details=f"Deactivated by admin: {current_user.username}"
    )
    
    return {"message": "User deactivated successfully"}
