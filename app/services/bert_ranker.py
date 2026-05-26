import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class BERTRanker:
    def __init__(self):
        self.model = None
        self.model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    def load_model(self):
        if self.model is None:
            logger.info(f"Loading BERT model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("✅ BERT model loaded successfully")
        return self.model
    
    def rank_cvs(self, job_description, cvs):
        logger.info(f"🔍 Ranking {len(cvs)} CVs")
        model = self.load_model()
        
        if not cvs:
            return []
        
        job_text = self._prepare_job_text(job_description)
        cv_texts = [self._prepare_cv_text(cv) for cv in cvs]
        
        job_embedding = model.encode([job_text])
        cv_embeddings = model.encode(cv_texts)
        similarities = cosine_similarity(job_embedding, cv_embeddings)[0]
        
        rankings = []
        for i, cv in enumerate(cvs):
            score = float(similarities[i])
            rankings.append({
                'cv_id': cv['id'],
                'score': score,
                'explanation': self._generate_explanation(cv, job_description, score)
            })
        
        rankings.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"✅ Rankings complete. Top score: {rankings[0]['score']:.2%}")
        return rankings
    
    def _prepare_job_text(self, job_data):
        if isinstance(job_data, dict):
            return f"{job_data.get('title', '')} {job_data.get('description', '')} {job_data.get('requirements', '')}".strip()
        return str(job_data)
    
    def _prepare_cv_text(self, cv):
        parts = []
        if cv.get('full_name'): parts.append(cv['full_name'])
        if cv.get('skills'): parts.append(' '.join(cv['skills']))
        if cv.get('nysc_info'): parts.append(cv['nysc_info'])
        if cv.get('siwes_info'): parts.append(cv['siwes_info'])
        if cv.get('raw_text'): parts.append(cv['raw_text'][:1000])
        return ' '.join(parts)
    
    def _generate_explanation(self, cv, job_description, score):
        features = []
        job_text = str(job_description).lower()
        
        if cv.get('skills'):
            for skill in cv['skills'][:5]:
                if skill.lower() in job_text:
                    features.append({'feature': f"Skill: {skill}", 'weight': 0.15})
        
        if cv.get('nysc_info') and 'nysc' in job_text:
            features.append({'feature': 'NYSC completed', 'weight': 0.10})
        
        if cv.get('siwes_info') and 'siwes' in job_text:
            features.append({'feature': 'SIWES experience', 'weight': 0.10})
        
        features.append({'feature': 'Overall semantic match', 'weight': score * 0.5})
        return {'top_features': features[:5]}

bert_ranker = BERTRanker()
