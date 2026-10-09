"""
Random forest endpoint: predicts recovery time in weeks.

Loads the model trained in random_forest/recovery_rf.ipynb:
  random_forest/recovery_rf.joblib   RandomForestRegressor trained on simulated patients

The mappings and column names below must match the notebook exactly.
If you change them there, change them here too.
"""
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/random-forest", tags=["Random Forest"])

MODEL_PATH = Path(__file__).resolve().parent.parent / "random_forest" / "recovery_rf.joblib"

# Same as the notebook
SEVERITY_MAP = {"Not severe at all": 1, "Mild": 3, "Moderate": 5, "Severe": 7, "Very severe": 9}
EXERCISE_MAP = {"I never exercise regularly.": 0, "I do not exercise at all.": 0,
                "I exercise sometimes.": 1, "I exercise most of the time.": 2, "I always exercise.": 3}
FEATURES = ["Age", "pain_severity", "exercise_level"]   # same columns and order as X in the notebook

_model = None


def _load():
    """Load the model once, on the first request."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise HTTPException(status_code=503,
                                detail="recovery_rf.joblib not found in the random_forest folder. "
                                       "Run the save cell in recovery_rf.ipynb.")
        import joblib
        _model = joblib.load(MODEL_PATH)
    return _model


class PatientProfile(BaseModel):
    age: float = Field(ge=1, le=120, examples=[40])
    pain_severity: Literal["Not severe at all", "Mild", "Moderate", "Severe", "Very severe"] = Field(
        examples=["Severe"])
    exercise_frequency: Literal["I never exercise regularly.", "I do not exercise at all.", "I exercise sometimes.",
                                "I exercise most of the time.", "I always exercise."] = Field(
        examples=["I exercise sometimes."])


@router.post("/predict")
def predict_recovery(profile: PatientProfile):
    """Predicted recovery time in weeks, plus the range the forest's trees agree on."""
    model = _load()

    # Same steps as the notebook: map text to numbers, same column names (no scaling for a random forest)
    row = pd.DataFrame([[profile.age, SEVERITY_MAP[profile.pain_severity],
                         EXERCISE_MAP[profile.exercise_frequency]]], columns=FEATURES)
    weeks = float(model.predict(row)[0])

    # Each tree makes its own guess; the middle 80% of those guesses gives a likely range
    tree_guesses = np.array([tree.predict(row.to_numpy())[0] for tree in model.estimators_])
    low, high = np.percentile(tree_guesses, [10, 90])

    return {
        "predicted_recovery_weeks": round(weeks, 1),
        "likely_range_weeks": [round(float(low), 1), round(float(high), 1)],
        "message": f"Estimated recovery: about {weeks:.0f} weeks (likely {low:.0f} to {high:.0f} weeks).",
        "note": "Trained on simulated recovery times shaped by the Pain Data survey. Not medical advice.",
    }


@router.get("/status")
def status():
    """Is the model file there?"""
    return {"model_file": MODEL_PATH.name, "ready": MODEL_PATH.exists()}
