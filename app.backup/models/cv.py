from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    file_type = Column(String(50), nullable=False)  # pdf or docx
    
    # Extracted text
    raw_text = Column(Text, nullable=False)
    parsed_data = Column(JSON, nullable=True)  # Structured extraction
    
    # Nigerian-specific fields (extracted)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    nysc_info = Column(Text, nullable=True)
    siwes_info = Column(Text, nullable=True)
    education = Column(JSON, nullable=True)  # List of degrees
    experience = Column(JSON, nullable=True)  # List of jobs
    skills = Column(JSON, nullable=True)  # List of skills
    
    # Metadata
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", backref="cvs")
    rankings = relationship("Ranking", back_populates="cv", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CV {self.filename}>"
