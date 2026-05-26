from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)
    experience_level: Optional[str] = Field(None, max_length=50)
    description: str = Field(..., min_length=50)
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)
    experience_level: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, min_length=50)
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    is_active: Optional[bool] = None


class JobResponse(BaseModel):
    id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    experience_level: Optional[str]
    description: str
    requirements: Optional[str]
    responsibilities: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class RankingRequest(BaseModel):
    job_id: int
    cv_ids: Optional[List[int]] = None  # If None, rank all user's CVs


class RankingResponse(BaseModel):
    id: int
    cv_id: int
    job_id: int
    relevance_score: float
    confidence: float
    rank_position: Optional[int]
    cv_filename: str
    created_at: datetime
    
    class Config:
        from_attributes = True
