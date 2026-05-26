from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.job import JobCreate, JobUpdate, JobResponse
from app.services.job_service import job_service
from app.models.user import User
from app.core.security import decode_token

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/", response_model=JobResponse, status_code=201)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new job description"""
    job = job_service.create_job(db, current_user.id, job_data)
    return job


@router.get("/", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all jobs for current user"""
    jobs = job_service.get_user_jobs(db, current_user.id, skip, limit, active_only)
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job details"""
    job = job_service.get_job(db, job_id, current_user.id)
    return job


@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update job"""
    job = job_service.update_job(db, job_id, current_user.id, job_data)
    return job


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete job"""
    job_service.delete_job(db, job_id, current_user.id)
    return {"message": "Job deleted successfully"}
