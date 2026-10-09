from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    injuries = relationship("InjuryLog", back_populates="user")
    pain_scores = relationship("PainScore", back_populates="user")
    recommendations = relationship("ExerciseRecommendation", back_populates="user")
    claims = relationship("InsuranceClaim", back_populates="user")
