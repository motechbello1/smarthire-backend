from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.ranking import Ranking
from app.core.security import decode_token
from app.ml.active_learner import active_learner

router = APIRouter(prefix="/feedback", tags=["Feedback & Active Learning"])


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


class FeedbackSubmit(BaseModel):
    ranking_id: int
    feedback: str  # 'good_fit', 'not_fit', 'maybe'
    comment: Optional[str] = None


@router.post("/submit")
def submit_feedback(
    data: FeedbackSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit recruiter feedback on a ranking"""
    
    # Validate feedback value
    valid_feedback = ['good_fit', 'not_fit', 'maybe']
    if data.feedback not in valid_feedback:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback. Must be one of: {', '.join(valid_feedback)}"
        )
    
    # Verify ranking belongs to user
    ranking = db.query(Ranking).filter(
        Ranking.id == data.ranking_id,
        Ranking.user_id == current_user.id
    ).first()
    
    if not ranking:
        raise HTTPException(status_code=404, detail="Ranking not found")
    
    success = active_learner.collect_feedback(
        db,
        data.ranking_id,
        data.feedback,
        data.comment
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    
    return {
        "message": "Feedback submitted successfully",
        "ranking_id": data.ranking_id,
        "feedback": data.feedback
    }


@router.get("/training-status")
def get_training_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active learning training status"""
    status = active_learner.can_retrain(db, current_user.id)
    return status


@router.get("/suggest-labels")
def suggest_labels(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get suggested rankings to label (uncertainty sampling)"""
    suggestions = active_learner.suggest_samples_for_labeling(db, current_user.id, limit)
    return {
        "suggestions": suggestions,
        "count": len(suggestions)
    }


@router.post("/retrain")
def retrain_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger model retraining with labeled data
    
    NOTE: This is a simulation. In production:
    - Would train actual BERT model
    - Run on background worker (Celery)
    - Take several minutes
    """
    result = active_learner.simulate_retraining(db, current_user.id)
    return result
