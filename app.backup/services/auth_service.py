from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    generate_verification_code,
    generate_reset_token
)
from app.core.config import settings


class AuthService:
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """Register a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate verification code
        verification_code = generate_verification_code()
        
        # Create new user
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            organization=user_data.organization,
            hashed_password=get_password_hash(user_data.password),
            verification_code=verification_code,
            is_verified=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Print verification code to console (mock email)
        print(f"\n{'='*50}")
        print(f"📧 EMAIL VERIFICATION CODE: {verification_code}")
        print(f"Send to: {user.email}")
        print(f"{'='*50}\n")
        
        return user
    
    @staticmethod
    def verify_email(db: Session, email: str, code: str) -> User:
        """Verify user's email with code"""
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        if user.verification_code != code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        # Mark as verified
        user.is_verified = True
        user.verification_code = None
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def login_user(db: Session, email: str, password: str) -> dict:
        """Authenticate user and return tokens"""
        
        # Debug logging
        print(f"\n🔍 LOGIN ATTEMPT: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"✅ User found: {user.email}, Verified: {user.is_verified}")
        else:
            print(f"❌ No user found with email: {email}")
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        print(f"🔐 Verifying password...")
        if not verify_password(password, user.hashed_password):
            print(f"❌ Password verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        print(f"✅ Password verified")
        
        if not user.is_verified:
            print(f"⚠️ User not verified")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email first"
            )
        
        print(f"✅ User is verified")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        print(f"✅ Tokens created successfully\n")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user
        }
    
    @staticmethod
    def logout_user(access_token: str):
        """Logout user by blacklisting token"""
        blacklist_token(access_token)
        return {"message": "Logged out successfully"}
    
    @staticmethod
    def request_password_reset(db: Session, email: str) -> str:
        """Generate password reset token"""
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Don't reveal if email exists or not
            return "If email exists, reset link has been sent"
        
        # Generate reset token
        reset_token = generate_reset_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        
        db.commit()
        
        # Print reset link to console (mock email)
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        print(f"\n{'='*50}")
        print(f"🔑 PASSWORD RESET LINK: {reset_link}")
        print(f"Send to: {user.email}")
        print(f"{'='*50}\n")
        
        return "If email exists, reset link has been sent"
    
    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> str:
        """Reset password using token"""
        user = db.query(User).filter(User.reset_token == token).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        if user.reset_token_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        
        db.commit()
        
        return "Password reset successfully"
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Generate new access token from refresh token"""
        payload = decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        access_token = create_access_token(data={"sub": user_id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }


# Singleton instance
auth_service = AuthService()