from pydantic import BaseModel

class InsuranceSchema(BaseModel):
    user_id: int
    claim_number: str
    injury_type: str
    predicted_cost: int
    predicted_recovery_days: int
