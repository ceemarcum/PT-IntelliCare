from pydantic import BaseModel

class InjurySchema(BaseModel):
    user_id: int
    injury_type: str
    symptoms: str
    severity: str
