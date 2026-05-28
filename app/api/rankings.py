from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import random

from app.core.database import get_db
from app.models.user import User
from app.models.cv import CV
from app.models.job import Job
from app.models.ranking import Ranking

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rankings", tags=["Rankings"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from app.core.security import decode_token
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def compute_score(cv, job_text: str) -> float:
    job_words = set(job_text.lower().split())

    cv_parts = []
    if cv.full_name:
        cv_parts.append(str(cv.full_name))
    if cv.skills:
        if isinstance(cv.skills, list):
            cv_parts.extend([str(s) for s in cv.skills])
        else:
            cv_parts.append(str(cv.skills))
    if cv.nysc_info:
        cv_parts.append(str(cv.nysc_info))
    if cv.siwes_info:
        cv_parts.append(str(cv.siwes_info))
    if cv.email:
        cv_parts.append(str(cv.email))

    cv_text = ' '.join(cv_parts).lower()
    cv_words = set(cv_text.split())

    if not job_words or not cv_words:
        return round(random.uniform(0.45, 0.75), 2)

    matches = len(job_words.intersection(cv_words))
    base_score = matches / max(len(job_words), 1)

    if cv.nysc_info:
        base_score += 0.10
    if cv.siwes_info:
        base_score += 0.05
    if cv.skills and len(cv.skills) > 3:
        base_score += 0.05

    final_score = min(max(base_score, 0.20), 0.95)
    return round(final_score, 2)


class RankingRequest(BaseModel):
    job_id: int


@router.post("/generate")
def generate_rankings(
    request_data: RankingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Generating rankings for job {request_data.job_id}")

    job = db.query(Job).filter(Job.id == request_data.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cvs = db.query(CV).filter(CV.user_id == current_user.id).all()
    if not cvs:
        raise HTTPException(status_code=400, detail="No CVs found")

    logger.info(f"Processing {len(cvs)} CVs")

    job_text = f"{job.title} {job.description} {job.requirements or ''}".strip()

    db.query(Ranking).filter(Ranking.job_id == job.id).delete()

    scored = []
    for cv in cvs:
        score = compute_score(cv, job_text)
        scored.append({'cv': cv, 'score': score})
        logger.info(f"CV {cv.id} ({cv.full_name}): {score:.2%}")

    scored.sort(key=lambda x: x['score'], reverse=True)

    for i, item in enumerate(scored):
        ranking = Ranking(
            job_id=job.id,
            cv_id=item['cv'].id,
            relevance_score=item['score'],
            confidence=item['score'],
            rank_position=i + 1,
            user_id=current_user.id,
            top_features=[
                {'feature': 'Overall keyword match', 'weight': item['score']},
                {'feature': 'NYSC completion', 'weight': 0.10 if item['cv'].nysc_info else 0},
                {'feature': 'SIWES experience', 'weight': 0.05 if item['cv'].siwes_info else 0},
            ]
        )
        db.add(ranking)

    db.commit()
    logger.info(f"Generated {len(scored)} rankings successfully")

    return {"message": f"Generated {len(scored)} rankings", "count": len(scored)}


@router.get("/job/{job_id}")
def get_job_rankings(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rankings = db.query(Ranking).filter(
        Ranking.job_id == job_id
    ).order_by(Ranking.relevance_score.desc()).all()

    logger.info(f"Found {len(rankings)} rankings for job {job_id}")

    result = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        result.append({
            'id': ranking.id,
            'score': float(ranking.relevance_score or 0),
            'explanation': {'top_features': ranking.top_features or []},
            'feedback': getattr(ranking, 'feedback', None),
            'cv': {
                'id': cv.id,
                'full_name': cv.full_name or 'Unknown',
                'email': cv.email or 'No email',
                'phone': getattr(cv, 'phone', None),
                'skills': cv.skills or [],
                'nysc_info': getattr(cv, 'nysc_info', None),
                'siwes_info': getattr(cv, 'siwes_info', None)
            } if cv else None
        })

    return result