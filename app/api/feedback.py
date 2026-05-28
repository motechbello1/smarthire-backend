from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.ranking import Ranking
from app.core.security import decode_token

router = APIRouter(prefix="/feedback", tags=["Feedback"])

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
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
    feedback: str
    comment: Optional[str] = None

@router.post("/")
def submit_feedback(
    data: FeedbackSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    valid_feedback = ['good_fit', 'not_fit', 'maybe']
    if data.feedback not in valid_feedback:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback. Must be one of: {', '.join(valid_feedback)}"
        )

    ranking = db.query(Ranking).filter(
        Ranking.id == data.ranking_id,
        Ranking.user_id == current_user.id
    ).first()

    if not ranking:
        raise HTTPException(status_code=404, detail="Ranking not found")

    ranking.feedback = data.feedback
    db.commit()

    return {
        "message": "Feedback submitted successfully",
        "ranking_id": data.ranking_id,
        "feedback": data.feedback
    }

@router.post("/submit")
def submit_feedback_alt(
    data: FeedbackSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return submit_feedback(data, current_user, db)