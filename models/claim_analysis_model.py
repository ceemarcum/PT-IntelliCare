from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from datetime import datetime

from database import Base


class ClaimAnalysis(Base):
    """The latest Insurance Analytics result for each claim (Step 6)."""
    __tablename__ = "claim_analyses"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("insurance_claims.id"), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    injury_type = Column(String)
    age = Column(Float)                    # claims don't store these, so the report saves them
    exercise_frequency = Column(String)
    risk_level = Column(String)
    risk_score = Column(Integer)
    reasons = Column(String)               # joined with " | "
    recovery_status = Column(String)
    predicted_weeks = Column(Float, nullable=True)
    weeks_since_claim = Column(Float)
    engagement_pct = Column(Integer)
    flagged = Column(Boolean, default=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
