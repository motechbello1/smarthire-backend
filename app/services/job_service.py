from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate
from typing import List, Optional


class JobService:
    
    @staticmethod
    def create_job(db: Session, user_id: int, job_data: JobCreate) -> Job:
        """Create new job"""
        job = Job(
            user_id=user_id,
            title=job_data.title,
            company=job_data.company,
            location=job_data.location,
            job_type=job_data.job_type,
            experience_level=job_data.experience_level,
            description=job_data.description,
            requirements=job_data.requirements,
            responsibilities=job_data.responsibilities,
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        return job
    
    @staticmethod
    def get_user_jobs(db: Session, user_id: int, skip: int = 0, limit: int = 100, active_only: bool = False) -> List[Job]:
        """Get all jobs for a user"""
        query = db.query(Job).filter(Job.user_id == user_id)
        
        if active_only:
            query = query.filter(Job.is_active == True)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_job(db: Session, job_id: int, user_id: int) -> Job:
        """Get single job by ID"""
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return job
    
    @staticmethod
    def update_job(db: Session, job_id: int, user_id: int, job_data: JobUpdate) -> Job:
        """Update job"""
        job = JobService.get_job(db, job_id, user_id)
        
        # Update only provided fields
        update_data = job_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        db.commit()
        db.refresh(job)
        
        return job
    
    @staticmethod
    def delete_job(db: Session, job_id: int, user_id: int) -> bool:
        """Delete job"""
        job = JobService.get_job(db, job_id, user_id)
        db.delete(job)
        db.commit()
        return True


job_service = JobService()
