from typing import List
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Mock email service that logs to console"""
    
    async def send_verification_email(self, email: str, code: str):
        """Send verification code email"""
        if settings.EMAIL_MOCK:
            logger.info(f"""
            ========================================
            EMAIL: Verification Code
            TO: {email}
            SUBJECT: Verify Your SmartHire AI Account
            
            Your verification code is: {code}
            
            This code expires in 15 minutes.
            
            If you didn't request this, please ignore this email.
            ========================================
            """)
            print(f"\n🔐 VERIFICATION CODE for {email}: {code}\n")
            return True
        else:
            # Real SMTP implementation would go here
            pass
    
    async def send_password_reset_email(self, email: str, reset_token: str):
        """Send password reset email"""
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        if settings.EMAIL_MOCK:
            logger.info(f"""
            ========================================
            EMAIL: Password Reset
            TO: {email}
            SUBJECT: Reset Your SmartHire AI Password
            
            Click the link below to reset your password:
            {reset_link}
            
            This link expires in 1 hour.
            
            If you didn't request this, please ignore this email.
            ========================================
            """)
            print(f"\n🔑 PASSWORD RESET LINK for {email}:\n{reset_link}\n")
            return True
        else:
            # Real SMTP implementation would go here
            pass
    
    async def send_welcome_email(self, email: str, full_name: str):
        """Send welcome email after verification"""
        if settings.EMAIL_MOCK:
            logger.info(f"""
            ========================================
            EMAIL: Welcome to SmartHire AI
            TO: {email}
            SUBJECT: Welcome to SmartHire AI!
            
            Hi {full_name},
            
            Your account is now verified and ready to use.
            
            You can now:
            - Upload CVs
            - Create job descriptions
            - Get AI-powered candidate rankings
            - Use LIME explanations
            
            Get started at: {settings.FRONTEND_URL}
            ========================================
            """)
            print(f"\n👋 WELCOME EMAIL sent to {email}\n")
            return True
        else:
            # Real SMTP implementation would go here
            pass


email_service = EmailService()
