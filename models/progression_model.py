from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime

from database import Base


class ProgressionState(Base):
    """Each user's current exercise level, set by the recommendation engine."""
    __tablename__ = "progression_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    level = Column(String, default="beginner")
    last_decision = Column(String)
    checkins_at_change = Column(Integer, default=0)   # how many check-ins the user had when the level last changed
    updated_at = Column(DateTime, default=datetime.utcnow)


class EngineNotification(Base):
    """Messages for the user when their plan changes or is paused."""
    __tablename__ = "engine_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    message = Column(String)
    decision = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
