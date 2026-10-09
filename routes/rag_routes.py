from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database_session import get_db
from models.injury_model import InjuryLog
from data_pipeline import injury_input

router = APIRouter(prefix="/rag", tags=["RAG"])


def _guidance(injury_type: str, pain_level: int, symptoms: str):
    # Imported here so the server still starts if the RAG isn't set up yet
    from rag.guidance import exercise_guidance
    try:
        return exercise_guidance(injury_type, pain_level, symptoms)
    except RuntimeError as exc:          # missing API key or vector store
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/guidance")
def rag_guidance(injury_type: str, pain_level: int, symptoms: str = ""):
    """Personalized exercise guidance: 'start with these' and 'avoid these for now'."""
    if not 0 <= pain_level <= 10:
        raise HTTPException(status_code=400, detail="pain_level must be 0-10")
    data = injury_input(injury_type, pain_level, symptoms, recovery_log="", exercise_log="")
    return _guidance(data["injury_type"], data["pain_level"], data["pain_symptoms"])


@router.post("/guidance/injury/{injury_id}")
def rag_guidance_for_injury(injury_id: int, db: Session = Depends(get_db)):
    """Same guidance, using an injury saved with POST /injury/submit."""
    injury = db.query(InjuryLog).filter(InjuryLog.id == injury_id).first()
    if not injury:
        raise HTTPException(status_code=404, detail="Injury not found")
    return _guidance(injury.injury_type, injury.pain_level, injury.symptoms or "")
