from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import logging

from ..database import get_db
from ..models import Ranking, CV, Job, User
from ..services.bert_ranker import bert_ranker
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rankings", tags=["rankings"])

class GenerateRankingsRequest(BaseModel):
    job_id: int

class FeedbackRequest(BaseModel):
    ranking_id: int
    feedback: str  # 'good_fit' or 'not_fit'

@router.post("/generate")
def generate_rankings(
    request: GenerateRankingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate rankings for a job using BERT"""
    logger.info(f"Generating rankings for job {request.job_id}")
    
    # Get job
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get all CVs for this user
    cvs = db.query(CV).filter(CV.user_id == current_user.id).all()
    
    if not cvs:
        raise HTTPException(status_code=400, detail="No CVs found. Please upload CVs first.")
    
    logger.info(f"Found {len(cvs)} CVs to rank")
    
    # Prepare CV data for BERT
    cv_data = []
    for cv in cvs:
        cv_dict = {
            'id': cv.id,
            'full_name': cv.full_name,
            'email': cv.email,
            'skills': cv.skills or [],
            'nysc_info': cv.nysc_info,
            'siwes_info': cv.siwes_info,
            'raw_text': cv.raw_text or ''
        }
        cv_data.append(cv_dict)
    
    # Prepare job data
    job_data = {
        'title': job.title,
        'description': job.description,
        'requirements': job.requirements or ''
    }
    
    # Generate rankings using BERT
    try:
        rankings_data = bert_ranker.rank_cvs(job_data, cv_data)
    except Exception as e:
        logger.error(f"BERT ranking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(e)}")
    
    # Delete old rankings for this job
    db.query(Ranking).filter(Ranking.job_id == job.id).delete()
    
    # Save rankings to database
    for rank_data in rankings_data:
        ranking = Ranking(
            job_id=job.id,
            cv_id=rank_data['cv_id'],
            score=rank_data['score'],
            explanation=rank_data['explanation']
        )
        db.add(ranking)
    
    db.commit()
    
    logger.info(f"Saved {len(rankings_data)} rankings to database")
    
    return {
        "message": f"Generated {len(rankings_data)} rankings successfully",
        "count": len(rankings_data)
    }

@router.get("/job/{job_id}")
def get_rankings_for_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all rankings for a specific job"""
    
    # Verify job exists and belongs to user
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get rankings with CV data
    rankings = db.query(Ranking).filter(Ranking.job_id == job_id).all()
    
    result = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        
        result.append({
            'id': ranking.id,
            'score': ranking.score,
            'explanation': ranking.explanation,
            'feedback': ranking.feedback,
            'cv': {
                'id': cv.id,
                'full_name': cv.full_name,
                'email': cv.email,
                'phone': cv.phone,
                'skills': cv.skills,
                'nysc_info': cv.nysc_info,
                'siwes_info': cv.siwes_info
            } if cv else None
        })
    
    return result

@router.post("/feedback")
def provide_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Provide feedback on a ranking"""
    
    ranking = db.query(Ranking).filter(Ranking.id == request.ranking_id).first()
    
    if not ranking:
        raise HTTPException(status_code=404, detail="Ranking not found")
    
    # Update feedback
    ranking.feedback = request.feedback
    db.commit()
    
    logger.info(f"Feedback recorded for ranking {request.ranking_id}: {request.feedback}")
    
    return {"message": "Feedback recorded successfully"}
