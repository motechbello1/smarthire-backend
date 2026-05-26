from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.job import RankingRequest, RankingResponse
from app.services.ranking_service import ranking_service
from app.models.user import User
from app.models.cv import CV
from app.core.security import decode_token

router = APIRouter(prefix="/rankings", tags=["Rankings"])


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


@router.post("/generate", response_model=List[RankingResponse])
def generate_rankings(
    request_data: RankingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate CV rankings for a job
    
    - Uses BERT semantic matching
    - Returns relevance scores and confidence
    - Ranks all user's CVs if cv_ids not provided
    """
    rankings = ranking_service.generate_rankings(
        db,
        current_user.id,
        request_data.job_id,
        request_data.cv_ids
    )
    
    # Format response with CV filename
    response = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        response.append(RankingResponse(
            id=ranking.id,
            cv_id=ranking.cv_id,
            job_id=ranking.job_id,
            relevance_score=ranking.relevance_score,
            confidence=ranking.confidence,
            rank_position=ranking.rank_position,
            cv_filename=cv.filename if cv else "Unknown",
            created_at=ranking.created_at
        ))
    
    return response


@router.get("/job/{job_id}", response_model=List[RankingResponse])
def get_job_rankings(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all rankings for a specific job"""
    rankings = ranking_service.get_job_rankings(db, job_id, current_user.id)
    
    response = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        response.append(RankingResponse(
            id=ranking.id,
            cv_id=ranking.cv_id,
            job_id=ranking.job_id,
            relevance_score=ranking.relevance_score,
            confidence=ranking.confidence,
            rank_position=ranking.rank_position,
            cv_filename=cv.filename if cv else "Unknown",
            created_at=ranking.created_at
        ))
    
    return response


@router.get("/cv/{cv_id}", response_model=List[RankingResponse])
def get_cv_rankings(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all rankings for a specific CV"""
    rankings = ranking_service.get_cv_rankings(db, cv_id, current_user.id)
    
    response = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        response.append(RankingResponse(
            id=ranking.id,
            cv_id=ranking.cv_id,
            job_id=ranking.job_id,
            relevance_score=ranking.relevance_score,
            confidence=ranking.confidence,
            rank_position=ranking.rank_position,
            cv_filename=cv.filename if cv else "Unknown",
            created_at=ranking.created_at
        ))
    
    return response
