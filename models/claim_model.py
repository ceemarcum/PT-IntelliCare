from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base

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
