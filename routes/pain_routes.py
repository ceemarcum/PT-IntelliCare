from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database_session import get_db
from models.pain_model import PainScore

router = APIRouter(prefix="/pain", tags=["Pain"])

@router.post("/submit")
def submit_pain_score(score: int, mobility: int, notes: str, user_id: int | None = None,
                      db: Session = Depends(get_db)):
    """Daily check-in. Add user_id so the recommendation engine can follow this user's pain trend."""
    new_score = PainScore(
        user_id=user_id,
        score=score,
        mobility=mobility,
        notes=notes
    )

    db.add(new_score)
    db.commit()
    db.refresh(new_score)

    return {
        "message": "Pain score logged successfully",
        "pain_score_id": new_score.id
    }


@router.get("/history/{user_id}")
def pain_history(user_id: int, db: Session = Depends(get_db)):
    """All check-ins for a user, oldest first."""
    rows = (db.query(PainScore).filter(PainScore.user_id == user_id)
            .order_by(PainScore.timestamp).all())
    return [{"id": r.id, "score": r.score, "mobility": r.mobility, "notes": r.notes,
             "timestamp": r.timestamp} for r in rows]
