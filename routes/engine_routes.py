"""
Dynamic Exercise Recommendation Engine (Step 5).

Combines:
  - Pain and mobility trends from the user's saved check-ins (POST /pain/submit with user_id)
  - Autoencoder anomaly alert   (routes/autoencoder_routes.py)
  - Recovery time model, Linear Regression (routes/recovery_routes.py)
  - RAG exercise guidance for the chosen level (rag/guidance.py)

The decision rules are in engine/rules.py.
"""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database_session import get_db
from engine.rules import trend, decide, pain_to_severity
from models.injury_model import InjuryLog
from models.pain_model import PainScore
from models.progression_model import ProgressionState, EngineNotification
from monitoring.metrics import record_decision

router = APIRouter(prefix="/engine", tags=["Recommendation Engine"])

ExerciseFrequency = Literal["I never exercise regularly.", "I do not exercise at all.", "I exercise sometimes.",
                            "I exercise most of the time.", "I always exercise."]


class RecommendRequest(BaseModel):
    user_id: int = Field(examples=[1])
    age: float = Field(ge=1, le=120, examples=[30])
    exercise_frequency: ExerciseFrequency = Field(examples=["I exercise sometimes."])
    include_guidance: bool = Field(default=True, description="Also get RAG exercise guidance (uses OpenAI)")


def _anomaly(age, severity, exercise_frequency):
    from routes.autoencoder_routes import check_profile, PainProfile
    try:
        return check_profile(PainProfile(age=age, pain_severity=severity, exercise_frequency=exercise_frequency))
    except HTTPException as exc:
        return {"is_anomaly": None, "note": f"Autoencoder unavailable: {exc.detail}"}


def _recovery(age, severity, exercise_frequency):
    from routes.recovery_routes import predict_recovery, PatientProfile
    try:
        return predict_recovery(PatientProfile(age=age, pain_severity=severity, exercise_frequency=exercise_frequency))
    except HTTPException as exc:
        return {"predicted_recovery_weeks": None, "note": f"Recovery model unavailable: {exc.detail}"}


def _guidance(injury_type, pain, symptoms, level):
    try:
        from rag.guidance import exercise_guidance
        return exercise_guidance(injury_type, int(round(pain)), symptoms, level=level)
    except Exception as exc:   # missing API key, vector store or OpenAI error: the rest still works
        return {"guidance": None, "note": f"RAG guidance unavailable: {exc}"}


@router.post("/recommend")
def recommend(req: RecommendRequest, db: Session = Depends(get_db)):
    """Check the user's recent check-ins and models, then set their exercise level."""
    injury = (db.query(InjuryLog).filter(InjuryLog.user_id == req.user_id)
              .order_by(InjuryLog.date_reported.desc()).first())
    if not injury:
        raise HTTPException(status_code=404,
                            detail="No injury found for this user. Submit one with POST /injury/submit and user_id.")

    checkins = (db.query(PainScore).filter(PainScore.user_id == req.user_id)
                .order_by(PainScore.timestamp).all())
    pain_values = [c.score for c in checkins]
    mobility_values = [c.mobility for c in checkins]
    latest_pain = pain_values[-1] if pain_values else injury.pain_level
    severity = pain_to_severity(latest_pain)

    # 1. Trends from saved check-ins
    pain_trend, mobility_trend = trend(pain_values), trend(mobility_values)

    # 2. Models
    anomaly = _anomaly(req.age, severity, req.exercise_frequency)
    recovery = _recovery(req.age, severity, req.exercise_frequency)

    # 3. Decide the new level
    state = db.query(ProgressionState).filter(ProgressionState.user_id == req.user_id).first()
    if state is None:
        state = ProgressionState(user_id=req.user_id, level="beginner", checkins_at_change=0)
        db.add(state)
    checkins_at_level = len(checkins) - (state.checkins_at_change or 0)
    result = decide(state.level, pain_trend, mobility_trend, anomaly.get("is_anomaly"), latest_pain, checkins_at_level)

    record_decision(result["decision"])

    if result["level_after"] != state.level:
        state.checkins_at_change = len(checkins)
    state.level, state.last_decision, state.updated_at = result["level_after"], result["decision"], datetime.utcnow()
    if result["notification"]:
        db.add(EngineNotification(user_id=req.user_id, message=result["notification"], decision=result["decision"]))
    db.commit()

    # 4. Recovery timeline: how far along the user is compared with the prediction
    weeks_so_far = round((datetime.utcnow() - injury.date_reported).days / 7, 1)
    predicted = recovery.get("predicted_recovery_weeks")
    timeline = {"weeks_since_injury": weeks_so_far, "predicted_recovery_weeks": predicted,
                "likely_range_weeks": recovery.get("likely_range_weeks")}
    if predicted:
        timeline["status"] = ("past the predicted recovery time" if weeks_so_far > recovery["likely_range_weeks"][1]
                              else "within the predicted recovery time")

    # 5. Exercises for the chosen level (RAG)
    guidance = (_guidance(injury.injury_type, latest_pain, injury.symptoms or "", result["level_after"])
                if req.include_guidance else None)

    return {
        "user_id": req.user_id,
        "injury_type": injury.injury_type,
        **result,
        "pain_trend": pain_trend,
        "mobility_trend": mobility_trend,
        "latest_pain": latest_pain,
        "checkins_used": len(checkins),
        "anomaly_check": anomaly,
        "recovery_timeline": timeline,
        "exercise_guidance": guidance,
    }


@router.get("/state/{user_id}")
def get_state(user_id: int, db: Session = Depends(get_db)):
    """The user's current exercise level."""
    state = db.query(ProgressionState).filter(ProgressionState.user_id == user_id).first()
    if not state:
        return {"user_id": user_id, "level": "beginner", "note": "No recommendation yet."}
    return {"user_id": user_id, "level": state.level, "last_decision": state.last_decision,
            "updated_at": state.updated_at}


@router.get("/notifications/{user_id}")
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    """Plan changes and pauses for this user, newest first."""
    rows = (db.query(EngineNotification).filter(EngineNotification.user_id == user_id)
            .order_by(EngineNotification.created_at.desc()).all())
    return [{"id": n.id, "message": n.message, "decision": n.decision, "created_at": n.created_at,
             "read": n.read} for n in rows]
