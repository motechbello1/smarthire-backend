from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from sqlalchemy.orm import Session
from app.models.ranking import Ranking
from app.models.cv import CV
from app.models.job import Job

logger = logging.getLogger(__name__)

class RankingService:
    def __init__(self):
        self.model = None
        self.model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    def _load_model(self):
        if self.model is None:
            logger.info(f"🔄 Loading BERT model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("✅ BERT model loaded successfully")
        return self.model
    
    def generate_rankings(self, db: Session, user_id: int, job_id: int, cv_ids=None):
        """Generate rankings using BERT semantic matching"""
        logger.info(f"🚀 Generating rankings for job {job_id}")
        
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError("Job not found")
        
        # Get CVs
        if cv_ids:
            cvs = db.query(CV).filter(CV.id.in_(cv_ids), CV.user_id == user_id).all()
        else:
            cvs = db.query(CV).filter(CV.user_id == user_id).all()
        
        if not cvs:
            raise ValueError("No CVs found")
        
        logger.info(f"📄 Processing {len(cvs)} CVs")
        
        # Load BERT model
        model = self._load_model()
        
        # Prepare job text
        job_text = f"{job.title} {job.description} {job.requirements or ''}".strip()
        
        # Prepare CV texts
        cv_data = []
        for cv in cvs:
            cv_text_parts = []
            if cv.full_name: cv_text_parts.append(cv.full_name)
            if cv.skills: cv_text_parts.append(' '.join(cv.skills))
            if cv.nysc_info: cv_text_parts.append(cv.nysc_info)
            if cv.siwes_info: cv_text_parts.append(cv.siwes_info)
            
            cv_data.append({
                'cv': cv,
                'text': ' '.join(cv_text_parts)
            })
        
        # Generate embeddings
        logger.info("🧠 Generating BERT embeddings...")
        job_embedding = model.encode([job_text])
        cv_texts = [item['text'] for item in cv_data]
        cv_embeddings = model.encode(cv_texts)
        
        # Calculate similarities
        similarities = cosine_similarity(job_embedding, cv_embeddings)[0]
        
        # Delete old rankings
        db.query(Ranking).filter(Ranking.job_id == job_id).delete()
        
        # Create new rankings
        rankings = []
        for i, item in enumerate(cv_data):
            score = float(similarities[i])
            
            ranking = Ranking(
                job_id=job_id,
                cv_id=item['cv'].id,
                relevance_score=score,
                confidence=score,  # For now, confidence = score
                rank_position=0  # Will be set after sorting
            )
            rankings.append(ranking)
        
        # Sort by score and assign positions
        rankings.sort(key=lambda x: x.relevance_score, reverse=True)
        for i, ranking in enumerate(rankings, 1):
            ranking.rank_position = i
            db.add(ranking)
        
        db.commit()
        
        logger.info(f"✅ Generated {len(rankings)} rankings. Top score: {rankings[0].relevance_score:.2%}")
        
        return rankings
    
    def get_job_rankings(self, db: Session, job_id: int, user_id: int):
        """Get all rankings for a job"""
        return db.query(Ranking).filter(Ranking.job_id == job_id).order_by(Ranking.rank_position).all()
    
    def get_cv_rankings(self, db: Session, cv_id: int, user_id: int):
        """Get all rankings for a CV"""
        return db.query(Ranking).filter(Ranking.cv_id == cv_id).order_by(Ranking.relevance_score.desc()).all()

# Singleton instance
ranking_service = RankingService()

