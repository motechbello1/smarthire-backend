from typing import Dict, List
from sqlalchemy.orm import Session
from app.models.ranking import Ranking
from app.models.cv import CV
from app.models.user import User
import statistics


class FairnessEvaluator:
    """
    Evaluate fairness of CV rankings
    
    Metrics:
    - Demographic Parity: P(selected | group A) ≈ P(selected | group B)
    - Equalized Odds: True positive rates equal across groups
    """
    
    def __init__(self):
        self.threshold_score = 0.7  # Score above which CV is "selected"
    
    def evaluate_demographic_parity(
        self,
        db: Session,
        job_id: int,
        demographic_field: str = 'gender'
    ) -> Dict:
        """
        Calculate demographic parity
        
        Measures if selection rates are equal across demographic groups
        """
        rankings = db.query(Ranking).filter(Ranking.job_id == job_id).all()
        
        if not rankings:
            return {'error': 'No rankings found for this job'}
        
        # Group rankings by demographic
        groups = {}
        for ranking in rankings:
            cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
            if not cv or not cv.parsed_data:
                continue
            
            # Extract demographic info from parsed_data
            demographic_value = cv.parsed_data.get(demographic_field, 'unknown')
            
            if demographic_value not in groups:
                groups[demographic_value] = {
                    'total': 0,
                    'selected': 0,
                    'scores': []
                }
            
            groups[demographic_value]['total'] += 1
            groups[demographic_value]['scores'].append(ranking.relevance_score)
            
            if ranking.relevance_score >= self.threshold_score:
                groups[demographic_value]['selected'] += 1
        
        # Calculate selection rates
        selection_rates = {}
        for group, data in groups.items():
            if data['total'] > 0:
                selection_rates[group] = data['selected'] / data['total']
            else:
                selection_rates[group] = 0
        
        # Calculate demographic parity score
        if len(selection_rates) >= 2:
            rates = list(selection_rates.values())
            max_rate = max(rates)
            min_rate = min(rates)
            parity_score = min_rate / max_rate if max_rate > 0 else 1.0
        else:
            parity_score = 1.0  # Perfect parity if only one group
        
        return {
            'metric': 'demographic_parity',
            'field': demographic_field,
            'groups': groups,
            'selection_rates': selection_rates,
            'parity_score': parity_score,
            'is_fair': parity_score >= 0.8,  # 80% rule
            'interpretation': self._interpret_parity(parity_score)
        }
    
    def evaluate_equalized_odds(
        self,
        db: Session,
        job_id: int,
        demographic_field: str = 'gender'
    ) -> Dict:
        """
        Calculate equalized odds
        
        Measures if true positive rates are equal across groups
        (requires ground truth labels from recruiter feedback)
        """
        rankings = db.query(Ranking).filter(
            Ranking.job_id == job_id,
            Ranking.feedback.isnot(None)  # Only labeled data
        ).all()
        
        if not rankings:
            return {'error': 'No labeled rankings found. Need recruiter feedback.'}
        
        # Group by demographic
        groups = {}
        for ranking in rankings:
            cv = db.query(CV).filter(CV.id == ranking.cv_id).first()
            if not cv or not cv.parsed_data:
                continue
            
            demographic_value = cv.parsed_data.get(demographic_field, 'unknown')
            
            if demographic_value not in groups:
                groups[demographic_value] = {
                    'true_positives': 0,
                    'false_positives': 0,
                    'true_negatives': 0,
                    'false_negatives': 0
                }
            
            # Ground truth from feedback
            actual_fit = (ranking.feedback == 'good_fit')
            predicted_fit = (ranking.relevance_score >= self.threshold_score)
            
            if actual_fit and predicted_fit:
                groups[demographic_value]['true_positives'] += 1
            elif not actual_fit and predicted_fit:
                groups[demographic_value]['false_positives'] += 1
            elif not actual_fit and not predicted_fit:
                groups[demographic_value]['true_negatives'] += 1
            else:
                groups[demographic_value]['false_negatives'] += 1
        
        # Calculate TPR and FPR for each group
        metrics = {}
        for group, data in groups.items():
            tp = data['true_positives']
            fp = data['false_positives']
            tn = data['true_negatives']
            fn = data['false_negatives']
            
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            metrics[group] = {
                'tpr': tpr,
                'fpr': fpr,
                'confusion_matrix': data
            }
        
        # Calculate equalized odds score
        if len(metrics) >= 2:
            tprs = [m['tpr'] for m in metrics.values()]
            max_tpr_diff = max(tprs) - min(tprs)
            odds_score = 1.0 - max_tpr_diff  # Closer to 1 = more fair
        else:
            odds_score = 1.0
        
        return {
            'metric': 'equalized_odds',
            'field': demographic_field,
            'groups': metrics,
            'odds_score': odds_score,
            'is_fair': odds_score >= 0.9,
            'interpretation': self._interpret_odds(odds_score)
        }
    
    def generate_fairness_report(
        self,
        db: Session,
        job_id: int
    ) -> Dict:
        """Generate comprehensive fairness report"""
        
        # Check both gender and ethnicity (if available)
        gender_parity = self.evaluate_demographic_parity(db, job_id, 'gender')
        ethnicity_parity = self.evaluate_demographic_parity(db, job_id, 'ethnicity')
        
        gender_odds = self.evaluate_equalized_odds(db, job_id, 'gender')
        
        return {
            'job_id': job_id,
            'demographic_parity': {
                'gender': gender_parity,
                'ethnicity': ethnicity_parity
            },
            'equalized_odds': {
                'gender': gender_odds
            },
            'overall_fairness': self._calculate_overall_fairness([
                gender_parity.get('parity_score', 1.0),
                ethnicity_parity.get('parity_score', 1.0),
                gender_odds.get('odds_score', 1.0)
            ])
        }
    
    def _interpret_parity(self, score: float) -> str:
        """Interpret demographic parity score"""
        if score >= 0.9:
            return "Excellent - No significant bias detected"
        elif score >= 0.8:
            return "Good - Meets 80% rule for fairness"
        elif score >= 0.7:
            return "Fair - Some disparity present"
        else:
            return "Poor - Significant disparity detected"
    
    def _interpret_odds(self, score: float) -> str:
        """Interpret equalized odds score"""
        if score >= 0.95:
            return "Excellent - Equal opportunity across groups"
        elif score >= 0.9:
            return "Good - Minimal bias in predictions"
        elif score >= 0.8:
            return "Fair - Some bias present"
        else:
            return "Poor - Significant bias in predictions"
    
    def _calculate_overall_fairness(self, scores: List[float]) -> Dict:
        """Calculate overall fairness score"""
        valid_scores = [s for s in scores if isinstance(s, (int, float))]
        if not valid_scores:
            return {'score': 1.0, 'status': 'unknown'}
        
        avg_score = statistics.mean(valid_scores)
        
        return {
            'score': avg_score,
            'status': 'fair' if avg_score >= 0.8 else 'biased',
            'interpretation': self._interpret_parity(avg_score)
        }


# Singleton instance
fairness_evaluator = FairnessEvaluator()
