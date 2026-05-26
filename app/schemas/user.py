from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: str
    organization: Optional[str] = None


class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    full_name: str
    organization: Optional[str] = None
    password: str = Field(..., min_length=8)


class UserRegister(BaseModel):
    """Schema for user registration (alias)"""
    email: EmailStr
    full_name: str
    organization: Optional[str] = None
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for user update"""
    full_name: Optional[str] = None
    organization: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    """Schema for email verification"""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"