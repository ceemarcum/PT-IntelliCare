from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database_session import get_db
from models.injury_model import InjuryLog

router = APIRouter(prefix="/injury", tags=["Injury"])

@router.post("/submit")
def submit_injury(injury_type: str, symptoms: str, pain_level: int, user_id: int | None = None,
                  db: Session = Depends(get_db)):
    """Report an injury. Add user_id so the recommendation engine knows whose injury it is."""
    new_injury = InjuryLog(
        user_id=user_id,
        injury_type=injury_type,
        symptoms=symptoms,
        pain_level=pain_level
    )
    db.add(new_injury)
    db.commit()
    db.refresh(new_injury)

    return {
        "message": "Injury logged successfully",
        "injury_id": new_injury.id
    }

@router.get("/user/{user_id}")
def user_injuries(user_id: int, db: Session = Depends(get_db)):
    """A user's injuries, newest first (used by the frontend)."""
    rows = (db.query(InjuryLog).filter(InjuryLog.user_id == user_id)
            .order_by(InjuryLog.date_reported.desc()).all())
    return [{"id": r.id, "injury_type": r.injury_type, "symptoms": r.symptoms,
             "pain_level": r.pain_level, "date_reported": r.date_reported} for r in rows]
