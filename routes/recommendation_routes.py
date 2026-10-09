from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database_session import get_db
from models.exercise_model import ExerciseRecommendation

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.post("/create")
def create_recommendation(
    user_id: int,
    injury_type: str,
    exercise_name: str,
    difficulty: str,
    frequency: str,
    db: Session = Depends(get_db)
):
    new_rec = ExerciseRecommendation(
        user_id=user_id,
        injury_type=injury_type,
        exercise_name=exercise_name,
        difficulty=difficulty,
        frequency=frequency
    )

    db.add(new_rec)
    db.commit()
    db.refresh(new_rec)

    return {
        "message": "Exercise recommendation created",
        "recommendation_id": new_rec.id
    }
