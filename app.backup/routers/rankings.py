from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models import Ranking, CV, Job, User
from app.services.bert_ranker import bert_ranker
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rankings", tags=["rankings"])

class GenerateRankingsRequest(BaseModel):
    job_id: int

@router.post("/generate")
def generate_rankings(
    request: GenerateRankingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Generating rankings for job {request.job_id}")
    
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    cvs = db.query(CV).filter(CV.user_id == current_user.id).all()
    if not cvs:
        raise HTTPException(status_code=400, detail="No CVs found")
    
    cv_data = [{
        'id': cv.id,
        'full_name': cv.full_name,
        'email': cv.email,
        'skills': cv.skills or [],
        'nysc_info': cv.nysc_info,
        'siwes_info': cv.siwes_info,
        'raw_text': getattr(cv, 'raw_text', '') or ''
    } for cv in cvs]
    
    job_data = {
        'title': job.title,
        'description': job.description,
        'requirements': job.requirements or ''
    }
    
    rankings_data = bert_ranker.rank_cvs(job_data, cv_data)
    
    db.query(Ranking).filter(Ranking.job_id == job.id).delete()
    
    for rank_data in rankings_data:
        ranking = Ranking(
            job_id=job.id,
            cv_id=rank_data['cv_id'],
            score=rank_data['score'],
            explanation=rank_data['explanation']
        )
        db.add(ranking)
    
    db.commit()
    return {"message": f"Generated {len(rankings_data)} rankings", "count": len(rankings_data)}

@router.get("/job/{job_id}")
def get_rankings(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rankings = db.query(Ranking).filter(Ranking.job_id == job_id).all()
    
    result = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        result.append({
            'id': ranking.id,
            'score': ranking.score or 0,
            'explanation': ranking.explanation or {},
            'feedback': ranking.feedback,
            'cv': {
                'id': cv.id,
                'full_name': cv.full_name or 'Unknown',
                'email': cv.email or 'No email',
                'phone': cv.phone,
                'skills': cv.skills or [],
                'nysc_info': cv.nysc_info,
                'siwes_info': cv.siwes_info
            } if cv else None
        })
    
    return result

@router.post("/feedback")
def feedback(ranking_id: int, feedback: str, db: Session = Depends(get_db)):
    ranking = db.query(Ranking).filter(Ranking.id == ranking_id).first()
    if not ranking:
        raise HTTPException(status_code=404, detail="Not found")
    ranking.feedback = feedback
    db.commit()
    return {"message": "Feedback recorded"}

