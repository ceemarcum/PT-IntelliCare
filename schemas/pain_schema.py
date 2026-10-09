from pydantic import BaseModel

class PainSchema(BaseModel):
    user_id: int
    pain_score: int
