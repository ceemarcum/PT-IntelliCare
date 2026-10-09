from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime

class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    claim_number = Column(String, unique=True)
    injury_type = Column(String)
    predicted_cost = Column(Integer)
    predicted_recovery_days = Column(Integer)
    date_filed = Column(DateTime, default=datetime.utcnow)
