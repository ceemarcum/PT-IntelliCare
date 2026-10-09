from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

class InjuryLog(Base):
    __tablename__ = "injury_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    injury_type = Column(String)
    symptoms = Column(String)
    pain_level = Column(Integer)
    date_reported = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="injuries")
