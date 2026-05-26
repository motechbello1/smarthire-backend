from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.core.security import decode_token
from app.ml.fairness_evaluator import fairness_evaluator

router = APIRouter(prefix="/fairness", tags=["Fairness Evaluation"])


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


@router.get("/demographic-parity/{job_id}")
def evaluate_demographic_parity(
    job_id: int,
    field: str = "gender",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate demographic parity for a job's rankings
    
    Measures if selection rates are equal across demographic groups
    """
    result = fairness_evaluator.evaluate_demographic_parity(db, job_id, field)
    return result


@router.get("/equalized-odds/{job_id}")
def evaluate_equalized_odds(
    job_id: int,
    field: str = "gender",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate equalized odds for a job's rankings
    
    Measures if true positive rates are equal across groups
    Requires labeled data from recruiter feedback
    """
    result = fairness_evaluator.evaluate_equalized_odds(db, job_id, field)
    return result


@router.get("/report/{job_id}")
def get_fairness_report(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive fairness report
    
    Includes:
    - Demographic parity (gender, ethnicity)
    - Equalized odds
    - Overall fairness score
    """
    report = fairness_evaluator.generate_fairness_report(db, job_id)
    return report
