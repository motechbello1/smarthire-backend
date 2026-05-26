from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.database import get_db
from app.schemas.user import (
    UserRegister,
    UserResponse,
    LoginRequest,
    VerifyEmailRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    RefreshTokenRequest,
    TokenResponse
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/15minutes")
def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Rate limit: 5 attempts per 15 minutes
    """
    user = auth_service.register_user(db, user_data)
    return user


@router.post("/verify-email", response_model=UserResponse)
@limiter.limit("5/15minutes")
def verify_email(
    request: Request,
    data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user's email with verification code
    
    Rate limit: 5 attempts per 15 minutes
    """
    user = auth_service.verify_email(db, data.email, data.code)
    return user


@router.post("/login")
@limiter.limit("5/15minutes")
def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT tokens
    
    Rate limit: 5 attempts per 15 minutes
    """
    print(f"\n📨 LOGIN REQUEST RECEIVED")
    print(f"Email: {credentials.email}")
    print(f"Password length: {len(credentials.password)}")
    
    try:
        result = auth_service.login_user(db, credentials.email, credentials.password)
        
        print(f"✅ Login successful, setting cookies...")
        
        # Set httpOnly cookies for security
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=604800  # 7 days
        )
        
        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": "bearer",
            "message": "Login successful"
        }
    
    except HTTPException as e:
        print(f"❌ Login failed: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
def logout(request: Request, response: Response):
    """Logout user by clearing cookies and blacklisting token"""
    access_token = request.cookies.get("access_token")
    
    if access_token:
        auth_service.logout_user(access_token)
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(
    request: Request,
    data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset
    
    Rate limit: 3 attempts per hour
    """
    message = auth_service.request_password_reset(db, data.email)
    return {"message": message}


@router.post("/reset-password")
@limiter.limit("5/15minutes")
def reset_password(
    request: Request,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password using token
    
    Rate limit: 5 attempts per 15 minutes
    """
    message = auth_service.reset_password(db, data.token, data.new_password)
    return {"message": message}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    data: RefreshTokenRequest
):
    """Refresh access token using refresh token"""
    result = auth_service.refresh_access_token(data.refresh_token)
    return result


@router.get("/me", response_model=UserResponse)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current logged-in user"""
    from app.models.user import User
    from app.core.security import decode_token
    
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user