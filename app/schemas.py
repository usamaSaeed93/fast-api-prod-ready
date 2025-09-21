from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class BackgroundJobCreate(BaseModel):
    job_type: str
    payload: Optional[dict] = None


class BackgroundJobResponse(BaseModel):
    id: int
    job_id: str
    job_type: str
    status: str
    payload: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    is_html: bool = False


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: dict
