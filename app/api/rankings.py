from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime
import re
from collections import Counter

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.core.database import get_db
from app.models.user import User
from app.models.cv import CV
from app.models.job import Job
from app.models.ranking import Ranking

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rankings", tags=["Rankings"])

bert_model = None

def load_bert_model():
    global bert_model
    if bert_model is None:
        logger.info("Loading BERT model...")
        bert_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("BERT model loaded!")
    return bert_model

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


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extract top keywords from text"""
    # Convert to lowercase and split into words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Remove common stopwords
    stopwords = {
        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'will', 'have',
        'are', 'was', 'were', 'been', 'being', 'has', 'had', 'can', 'could',
        'should', 'would', 'may', 'might', 'must', 'shall', 'about', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'between',
        'under', 'over', 'out', 'off', 'down', 'then', 'once', 'here', 'there',
        'when', 'where', 'why', 'how', 'all', 'each', 'other', 'some', 'such',
        'only', 'own', 'same', 'than', 'too', 'very', 'can', 'just', 'don',
        'now', 'also', 'work', 'experience', 'role', 'position', 'job'
    }
    
    filtered_words = [w for w in words if w not in stopwords]
    
    # Get most common words
    word_counts = Counter(filtered_words)
    return [word for word, count in word_counts.most_common(top_n)]


def calculate_skill_match(cv_skills: List[str], job_text: str) -> Dict[str, Any]:
    """Calculate how many CV skills match job requirements"""
    if not cv_skills:
        return {
            'matched_skills': [],
            'match_percentage': 0,
            'total_cv_skills': 0
        }
    
    job_text_lower = job_text.lower()
    matched = []
    
    for skill in cv_skills:
        if skill.lower() in job_text_lower:
            matched.append(skill)
    
    match_percentage = (len(matched) / len(cv_skills) * 100) if cv_skills else 0
    
    return {
        'matched_skills': matched,
        'match_percentage': round(match_percentage, 1),
        'total_cv_skills': len(cv_skills)
    }


def calculate_keyword_overlap(cv_text: str, job_text: str) -> Dict[str, Any]:
    """Calculate keyword overlap between CV and job"""
    cv_keywords = set(extract_keywords(cv_text, top_n=20))
    job_keywords = set(extract_keywords(job_text, top_n=20))
    
    common_keywords = cv_keywords.intersection(job_keywords)
    
    overlap_percentage = (len(common_keywords) / len(job_keywords) * 100) if job_keywords else 0
    
    return {
        'common_keywords': list(common_keywords)[:8],  # Top 8 matching keywords
        'overlap_percentage': round(overlap_percentage, 1),
        'total_job_keywords': len(job_keywords)
    }


def generate_explanation(cv: CV, job: Job, similarity_score: float) -> Dict[str, Any]:
    """Generate detailed explanation for the ranking score"""
    
    # Build job text
    job_text = f"{job.title} {job.description} {job.requirements or ''}".strip()
    
    # Build CV text
    cv_parts = []
    if cv.full_name: cv_parts.append(cv.full_name)
    if cv.skills: cv_parts.append(' '.join(cv.skills))
    if cv.nysc_info: cv_parts.append(cv.nysc_info)
    if cv.siwes_info: cv_parts.append(cv.siwes_info)
    cv_text = ' '.join(cv_parts)
    
    # Calculate skill match
    skill_analysis = calculate_skill_match(cv.skills or [], job_text)
    
    # Calculate keyword overlap
    keyword_analysis = calculate_keyword_overlap(cv_text, job_text)
    
    # Determine match category
    score_percent = similarity_score * 100
    if score_percent >= 70:
        match_category = "Excellent"
        match_color = "green"
    elif score_percent >= 50:
        match_category = "Good"
        match_color = "blue"
    elif score_percent >= 30:
        match_category = "Fair"
        match_color = "orange"
    else:
        match_category = "Poor"
        match_color = "red"
    
    # Build explanation
    explanation = {
        'overall_score': round(score_percent, 1),
        'match_category': match_category,
        'match_color': match_color,
        'skill_match': skill_analysis,
        'keyword_overlap': keyword_analysis,
        'breakdown': [
            {
                'category': 'Skills Match',
                'score': skill_analysis['match_percentage'],
                'weight': 0.4,
                'details': f"{len(skill_analysis['matched_skills'])} out of {skill_analysis['total_cv_skills']} skills match"
            },
            {
                'category': 'Keyword Relevance',
                'score': keyword_analysis['overlap_percentage'],
                'weight': 0.3,
                'details': f"{len(keyword_analysis['common_keywords'])} common keywords found"
            },
            {
                'category': 'Overall Semantic Match',
                'score': score_percent,
                'weight': 0.3,
                'details': f"BERT similarity score: {round(similarity_score, 3)}"
            }
        ],
        'top_matched_skills': skill_analysis['matched_skills'][:5],
        'top_keywords': keyword_analysis['common_keywords'][:5],
        'summary': f"This candidate has a {match_category.lower()} match with {len(skill_analysis['matched_skills'])} relevant skills and {len(keyword_analysis['common_keywords'])} matching keywords."
    }
    
    return explanation


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
    
    model = load_bert_model()
    job_text = f"{job.title} {job.description} {job.requirements or ''}".strip()
    
    cv_data = []
    for cv in cvs:
        parts = []
        if cv.full_name: parts.append(cv.full_name)
        if cv.skills: parts.append(' '.join(cv.skills))
        if cv.nysc_info: parts.append(cv.nysc_info)
        if cv.siwes_info: parts.append(cv.siwes_info)
        cv_data.append({'cv': cv, 'text': ' '.join(parts)})
    
    logger.info("Generating embeddings...")
    job_embedding = model.encode([job_text])
    cv_texts = [item['text'] for item in cv_data]
    cv_embeddings = model.encode(cv_texts)
    similarities = cosine_similarity(job_embedding, cv_embeddings)[0]
    
    # Delete old rankings for this job
    db.query(Ranking).filter(Ranking.job_id == job.id).delete()
    
    # Sort by similarity score (descending)
    sorted_indices = np.argsort(similarities)[::-1]
    
    # Save new rankings to database with detailed explanations
    rankings = []
    for rank_position, idx in enumerate(sorted_indices, start=1):
        cv = cv_data[idx]['cv']
        score = float(similarities[idx])
        
        # Generate detailed explanation
        explanation = generate_explanation(cv, job, score)
        
        # CRITICAL: Store score as 0-1 range (not percentage)
        ranking = Ranking(
            job_id=job.id,
            cv_id=cv.id,
            relevance_score=score,  # Store as 0-1 range
            confidence=score,
            rank_position=rank_position,
            user_id=current_user.id,
            top_features=explanation  # Store full explanation as JSON
        )
        db.add(ranking)
        rankings.append({'score': score, 'rank': rank_position})
    
    db.commit()
    logger.info(f"Generated {len(rankings)} rankings with detailed explanations")
    
    return {
        "message": f"Generated {len(rankings)} rankings with detailed explanations",
        "count": len(rankings)
    }


@router.get("/job/{job_id}")
def get_job_rankings(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rankings from database with full explanations"""
    rankings = db.query(Ranking).filter(
        Ranking.job_id == job_id
    ).order_by(Ranking.relevance_score.desc()).all()
    
    logger.info(f"Found {len(rankings)} rankings for job {job_id}")
    
    result = []
    for ranking in rankings:
        cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
        
        # CRITICAL: Handle both old data (already percentage) and new data (0-1 range)
        if ranking.relevance_score <= 1.0:
            # New format: 0-1 range, convert to percentage
            display_score = round(ranking.relevance_score * 100, 1)
        else:
            # Old format: already a percentage
            display_score = round(ranking.relevance_score, 1)
        
        # Get explanation (should already be stored)
        explanation = ranking.top_features if ranking.top_features else {
            'overall_score': display_score,
            'match_category': 'Unknown',
            'summary': 'No detailed explanation available',
            'breakdown': [],
            'top_matched_skills': [],
            'top_keywords': []
        }
        
        # Ensure explanation has overall_score that matches display_score
        if isinstance(explanation, dict):
            explanation['overall_score'] = display_score
        
        result.append({
            'id': ranking.id,
            'score': display_score,
            'explanation': explanation,
            'feedback': ranking.feedback,
            'rank_position': ranking.rank_position,
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