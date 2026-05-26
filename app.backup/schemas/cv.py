from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class CVUpload(BaseModel):
    filename: str
    file_size: int
    file_type: str


class CVResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    file_type: str
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    nysc_info: Optional[str]
    siwes_info: Optional[str]
    skills: Optional[List[str]]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CVDetail(CVResponse):
    raw_text: str
    parsed_data: Optional[Dict]
    education: Optional[List[Dict]]
    experience: Optional[List[Dict]]
    
    class Config:
        from_attributes = True
