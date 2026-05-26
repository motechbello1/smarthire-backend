from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.cv import CVResponse, CVDetail
from app.services.cv_service import cv_service
from app.models.user import User
from app.core.security import decode_token

router = APIRouter(prefix="/cvs", tags=["CVs"])


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


@router.post("/upload", response_model=CVResponse, status_code=201)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process CV
    
    - Accepts PDF or DOCX files
    - Maximum size: 5MB
    - Automatically extracts text and Nigerian-specific info
    """
    cv = await cv_service.upload_cv(db, current_user.id, file)
    return cv


@router.get("/", response_model=List[CVResponse])
def list_cvs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all CVs for current user"""
    cvs = cv_service.get_user_cvs(db, current_user.id, skip, limit)
    return cvs


@router.get("/{cv_id}", response_model=CVDetail)
def get_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed CV information"""
    cv = cv_service.get_cv(db, cv_id, current_user.id)
    return cv


@router.delete("/{cv_id}")
def delete_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete CV"""
    cv_service.delete_cv(db, cv_id, current_user.id)
    return {"message": "CV deleted successfully"}
