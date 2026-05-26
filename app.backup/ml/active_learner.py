from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models.ranking import Ranking
from app.models.cv import CV
from app.models.job import Job


class ActiveLearner:
    """Active learning system for improving rankings with recruiter feedback"""
    
    def __init__(self):
        self.min_samples_for_training = 20  # Minimum labeled samples
        self.target_accuracy = 0.75  # 75% accuracy target
    
    def collect_feedback(
        self,
        db: Session,
        ranking_id: int,
        feedback: str,
        comment: str = None
    ) -> bool:
        """
        Collect recruiter feedback on a ranking
        
        Args:
            ranking_id: ID of the ranking
            feedback: 'good_fit', 'not_fit', 'maybe'
            comment: Optional comment
        """
        ranking = db.query(Ranking).filter(Ranking.id == ranking_id).first()
        if not ranking:
            return False
        
        ranking.feedback = feedback
        ranking.feedback_comment = comment
        
        from datetime import datetime
        ranking.feedback_at = datetime.utcnow()
        
        db.commit()
        return True
    
    def get_training_data(self, db: Session, user_id: int) -> List[Dict]:
        """Get all labeled rankings for a user"""
        rankings = db.query(Ranking).filter(
            Ranking.user_id == user_id,
            Ranking.feedback.isnot(None)
        ).all()
        
        training_data = []
        for ranking in rankings:
            cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
            job = db.query(Job).filter(Job.id == ranking.job_id).first()
            
            if cv and job:
                # Convert feedback to binary label
                label = 1 if ranking.feedback == 'good_fit' else 0
                
                training_data.append({
                    'cv_text': cv.raw_text,
                    'job_text': f"{job.title}\n{job.description}\n{job.requirements or ''}",
                    'label': label,
                    'relevance_score': ranking.relevance_score
                })
        
        return training_data
    
    def can_retrain(self, db: Session, user_id: int) -> Dict:
        """Check if we have enough labeled data to retrain"""
        training_data = self.get_training_data(db, user_id)
        
        total_samples = len(training_data)
        positive_samples = sum(1 for d in training_data if d['label'] == 1)
        negative_samples = total_samples - positive_samples
        
        can_train = total_samples >= self.min_samples_for_training
        
        return {
            'can_retrain': can_train,
            'total_samples': total_samples,
            'positive_samples': positive_samples,
            'negative_samples': negative_samples,
            'min_required': self.min_samples_for_training,
            'samples_needed': max(0, self.min_samples_for_training - total_samples)
        }
    
    def suggest_samples_for_labeling(
        self,
        db: Session,
        user_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """
        Use uncertainty sampling to suggest which rankings to label next
        
        Returns rankings with confidence scores closest to 0.5 (most uncertain)
        """
        unlabeled_rankings = db.query(Ranking).filter(
            Ranking.user_id == user_id,
            Ranking.feedback.is_(None)
        ).all()
        
        # Calculate uncertainty (distance from 0.5)
        uncertain_rankings = []
        for ranking in unlabeled_rankings:
            uncertainty = abs(ranking.confidence - 0.5)
            uncertain_rankings.append({
                'ranking_id': ranking.id,
                'cv_id': ranking.cv_id,
                'job_id': ranking.job_id,
                'relevance_score': ranking.relevance_score,
                'confidence': ranking.confidence,
                'uncertainty': uncertainty
            })
        
        # Sort by uncertainty (ascending - most uncertain first)
        uncertain_rankings.sort(key=lambda x: x['uncertainty'])
        
        return uncertain_rankings[:limit]
    
    def simulate_retraining(self, db: Session, user_id: int) -> Dict:
        """
        Simulate model retraining with current labeled data
        
        In production, this would:
        1. Train a new BERT model on labeled data
        2. Evaluate on validation set
        3. Deploy if accuracy > threshold
        
        For now, we simulate the process
        """
        status = self.can_retrain(db, user_id)
        
        if not status['can_retrain']:
            return {
                'success': False,
                'message': f"Need {status['samples_needed']} more labeled samples"
            }
        
        training_data = self.get_training_data(db, user_id)
        
        # Simulate training metrics
        import random
        simulated_accuracy = min(
            self.target_accuracy + random.uniform(-0.05, 0.10),
            0.95
        )
        
        return {
            'success': True,
            'accuracy': simulated_accuracy,
            'training_samples': len(training_data),
            'meets_target': simulated_accuracy >= self.target_accuracy,
            'message': f"Model retrained with {simulated_accuracy:.1%} accuracy"
        }


# Singleton instance
active_learner = ActiveLearner()
