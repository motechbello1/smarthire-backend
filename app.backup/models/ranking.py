from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("cvs.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Ranking scores
    relevance_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    rank_position = Column(Integer, nullable=True)
    
    # LIME explanations (Phase 3)
    top_features = Column(JSON, nullable=True)
    explanation_fidelity = Column(Float, nullable=True)
    
    # Active learning feedback (Phase 3)
    feedback = Column(Text, nullable=True)  # Changed from String to Text
    feedback_comment = Column(Text, nullable=True)
    feedback_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cv = relationship("CV", back_populates="rankings")
    job = relationship("Job", back_populates="rankings")
    user = relationship("User", backref="rankings")

    def __repr__(self):
        return f"<Ranking CV:{self.cv_id} Job:{self.job_id} Score:{self.relevance_score:.2f}>"