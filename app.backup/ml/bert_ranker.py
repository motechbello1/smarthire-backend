from typing import List, Tuple
import numpy as np


class BERTRanker:
    """BERT-based semantic similarity ranking"""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained sentence transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            # Use a lightweight multilingual model
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✓ BERT model loaded successfully")
        except ImportError:
            print("⚠ sentence-transformers not installed, using fallback")
            self.model = None
        except Exception as e:
            print(f"⚠ Model load failed: {e}, using fallback")
            self.model = None
    
    def rank_cvs(self, job_description: str, cv_texts: List[str]) -> List[Tuple[int, float, float]]:
        """
        Rank CVs against job description
        
        Returns: List of (cv_index, relevance_score, confidence)
        """
        if self.model is None:
            # Fallback: simple keyword matching
            return self._fallback_ranking(job_description, cv_texts)
        
        try:
            # Encode job description
            job_embedding = self.model.encode([job_description])[0]
            
            # Encode all CVs
            cv_embeddings = self.model.encode(cv_texts)
            
            # Calculate cosine similarity
            scores = []
            for idx, cv_emb in enumerate(cv_embeddings):
                similarity = self._cosine_similarity(job_embedding, cv_emb)
                confidence = min(1.0, similarity + 0.1)  # Simple confidence estimate
                scores.append((idx, float(similarity), float(confidence)))
            
            # Sort by relevance score (descending)
            scores.sort(key=lambda x: x[1], reverse=True)
            
            return scores
            
        except Exception as e:
            print(f"⚠ BERT ranking failed: {e}, using fallback")
            return self._fallback_ranking(job_description, cv_texts)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def _fallback_ranking(self, job_description: str, cv_texts: List[str]) -> List[Tuple[int, float, float]]:
        """Simple keyword-based fallback ranking"""
        # Extract keywords from job description
        job_words = set(job_description.lower().split())
        
        scores = []
        for idx, cv_text in enumerate(cv_texts):
            cv_words = set(cv_text.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(job_words & cv_words)
            union = len(job_words | cv_words)
            
            if union > 0:
                similarity = intersection / union
            else:
                similarity = 0.0
            
            # Normalize to 0-1 range
            relevance = min(1.0, similarity * 3)  # Scale up
            confidence = 0.5  # Low confidence for fallback
            
            scores.append((idx, relevance, confidence))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


# Singleton instance
bert_ranker = BERTRanker()
