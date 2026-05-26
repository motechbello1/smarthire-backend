from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.ranking import Ranking
from app.models.cv import CV
from app.models.job import Job
from app.ml.bert_ranker import bert_ranker
from app.ml.lime_explainer import lime_explainer
from typing import List, Optional
import json


class RankingService:
    
    @staticmethod
    def generate_rankings(
        db: Session,
        user_id: int,
        job_id: int,
        cv_ids: Optional[List[int]] = None,
        include_explanations: bool = True
    ) -> List[Ranking]:
        """Generate rankings for CVs against a job with LIME explanations"""
        
        # Get job
        job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Get CVs to rank
        if cv_ids:
            cvs = db.query(CV).filter(
                CV.id.in_(cv_ids),
                CV.user_id == user_id
            ).all()
        else:
            # Rank all user's CVs
            cvs = db.query(CV).filter(CV.user_id == user_id).all()
        
        if not cvs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No CVs found to rank"
            )
        
        # Prepare texts for ranking
        job_text = f"{job.title}\n{job.description}\n{job.requirements or ''}"
        cv_texts = [cv.raw_text for cv in cvs]
        
        # Get rankings from BERT
        bert_scores = bert_ranker.rank_cvs(job_text, cv_texts)
        
        # Delete existing rankings for this job
        db.query(Ranking).filter(
            Ranking.job_id == job_id,
            Ranking.user_id == user_id
        ).delete()
        
        # Create new ranking records with LIME explanations
        rankings = []
        for rank_position, (cv_idx, relevance_score, confidence) in enumerate(bert_scores, start=1):
            cv = cvs[cv_idx]
            
            # Generate LIME explanation
            top_features = None
            explanation_fidelity = None
            
            if include_explanations:
                explanation = lime_explainer.explain_ranking(
                    cv.raw_text,
                    job_text,
                    relevance_score
                )
                top_features = explanation['top_features']
                explanation_fidelity = explanation['fidelity']
            
            ranking = Ranking(
                cv_id=cv.id,
                job_id=job_id,
                user_id=user_id,
                relevance_score=relevance_score,
                confidence=confidence,
                rank_position=rank_position,
                top_features=top_features,  # LIME features
                explanation_fidelity=explanation_fidelity  # R² score
            )
            
            db.add(ranking)
            rankings.append(ranking)
        
        db.commit()
        
        # Refresh all rankings
        for ranking in rankings:
            db.refresh(ranking)
        
        return rankings
    
    @staticmethod
    def get_job_rankings(db: Session, job_id: int, user_id: int) -> List[Ranking]:
        """Get all rankings for a job"""
        return db.query(Ranking).filter(
            Ranking.job_id == job_id,
            Ranking.user_id == user_id
        ).order_by(Ranking.rank_position).all()
    
    @staticmethod
    def get_cv_rankings(db: Session, cv_id: int, user_id: int) -> List[Ranking]:
        """Get all rankings for a CV"""
        return db.query(Ranking).filter(
            Ranking.cv_id == cv_id,
            Ranking.user_id == user_id
        ).order_by(Ranking.relevance_score.desc()).all()


ranking_service = RankingService()
