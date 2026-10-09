from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


# -------------------------
# 1. USER PROFILES
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    injuries = relationship("InjuryLog", back_populates="user")
    pain_scores = relationship("PainScore", back_populates="user")
    recommendations = relationship("ExerciseRecommendation", back_populates="user")
    claims = relationship("InsuranceClaim", back_populates="user")


# -------------------------
# 2. INJURY LOGS
# -------------------------
class InjuryLog(Base):
    __tablename__ = "injury_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    injury_type = Column(String)
    symptoms = Column(String)
    pain_level = Column(Integer)
    date_reported = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="injuries")


# -------------------------
# 3. PAIN SCORES
# -------------------------
class PainScore(Base):
    __tablename__ = "pain_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer)
    mobility = Column(Integer)
    notes = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pain_scores")


# -------------------------
# 4. EXERCISE RECOMMENDATIONS
# -------------------------
class ExerciseRecommendation(Base):
    __tablename__ = "exercise_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    injury_type = Column(String)
    exercise_name = Column(String)
    difficulty = Column(String)
    frequency = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recommendations")


# -------------------------
# 5. INSURANCE CLAIM METADATA
# -------------------------
class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    injury_type = Column(String)
    claim_date = Column(DateTime)
    expected_recovery_weeks = Column(Integer)
    actual_recovery_weeks = Column(Integer, nullable=True)
    flagged = Column(Boolean, default=False)

    user = relationship("User", back_populates="claims")
