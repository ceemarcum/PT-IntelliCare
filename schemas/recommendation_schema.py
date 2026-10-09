from pydantic import BaseModel

class RecommendationSchema(BaseModel):
    user_id: int
    exercise_name: str
    description: str
    predicted_recovery_days: int
