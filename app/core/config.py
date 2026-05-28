from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./smarthire.db"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production-min-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    FRONTEND_URL: str = "https://smarthire-frontend-gamma.vercel.app"
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "https://smarthire-frontend-gamma.vercel.app",
    ]
    
    # Email (Mock for now)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@smarthire.ai"
    EMAIL_MOCK: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    LOGIN_RATE_LIMIT: str = "5/15minute"
    
    # File Upload
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_FILE_TYPES: list = [".pdf", ".docx"]
    
    # Application
    PROJECT_NAME: str = "SmartHire AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()