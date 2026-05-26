from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job details
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=True)  # full-time, contract, etc
    experience_level = Column(String(50), nullable=True)  # entry, mid, senior
    
    # Description
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    
    # Parsed requirements
    required_skills = Column(JSON, nullable=True)
    preferred_skills = Column(JSON, nullable=True)
    education_requirement = Column(String(100), nullable=True)
    years_experience = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="jobs")
    rankings = relationship("Ranking", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job {self.title}>"
