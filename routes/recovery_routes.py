"""
Recovery time model endpoint: predicts recovery time in weeks with Linear Regression.

Loads the model trained in linear_regression/recovery_lr.ipynb:
  linear_regression/recovery_lr.joblib   LinearRegression trained on simulated patients

Linear Regression replaced the random forest because it scored better in 5-fold cross-validation
(RMSE 1.48 vs 1.55 weeks). routes/random_forest_routes.py is kept for reference but no longer loaded.

The mappings and column names below must match the notebook exactly.
"""
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from monitoring.metrics import record_recovery

router = APIRouter(prefix="/recovery-model", tags=["Recovery Model (Linear Regression)"])

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "linear_regression" / "recovery_lr.joblib"
HISTORY_PATH = BASE_DIR / "data" / "historical_recovery.csv"   # the data the model learned from

# Same as the notebook
SEVERITY_MAP = {"Not severe at all": 1, "Mild": 3, "Moderate": 5, "Severe": 7, "Very severe": 9}
EXERCISE_MAP = {"I never exercise regularly.": 0, "I do not exercise at all.": 0,
                "I exercise sometimes.": 1, "I exercise most of the time.": 2, "I always exercise.": 3}
FEATURES = ["Age", "pain_severity", "exercise_level"]   # same columns and order as X in the notebook

Z_80 = 1.2816      # 80% of patients fall within +/- 1.28 typical errors (same 10th-90th range the forest used)
MIN_WEEKS = 2      # the simulation never goes below 2 weeks

_model = None
_typical_error = None


def _load():
    """Load the model once, and measure its typical error (residual SD) on the historical data."""
    global _model, _typical_error
    if _model is None:
        if not MODEL_PATH.exists():
            raise HTTPException(status_code=503,
                                detail="recovery_lr.joblib not found in the linear_regression folder. "
                                       "Run linear_regression/recovery_lr.ipynb.")
        import joblib
        _model = joblib.load(MODEL_PATH)
        if HISTORY_PATH.exists():
            hist = pd.read_csv(HISTORY_PATH)
            residuals = hist["recovery_weeks"] - _model.predict(hist[FEATURES])
            _typical_error = float(np.std(residuals))
        else:
            _typical_error = 1.5   # the simulation's noise level, if the CSV is missing
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
    """Predicted recovery time in weeks, plus the range most similar patients fall in."""
    model = _load()

    # Same steps as the notebook: map text to numbers, same column names (no scaling needed)
    row = pd.DataFrame([[profile.age, SEVERITY_MAP[profile.pain_severity],
                         EXERCISE_MAP[profile.exercise_frequency]]], columns=FEATURES)
    weeks = max(float(model.predict(row)[0]), MIN_WEEKS)

    # Likely range: prediction +/- 1.28 typical errors covers about 80% of patients
    low = max(weeks - Z_80 * _typical_error, MIN_WEEKS)
    high = weeks + Z_80 * _typical_error

    record_recovery(profile.age, profile.pain_severity, profile.exercise_frequency, round(weeks, 1))

    return {
        "predicted_recovery_weeks": round(weeks, 1),
        "likely_range_weeks": [round(low, 1), round(high, 1)],
        "message": f"Estimated recovery: about {weeks:.0f} weeks (likely {low:.0f} to {high:.0f} weeks).",
        "model": "linear_regression",
        "note": "Trained on simulated recovery times shaped by the Pain Data survey. Not medical advice.",
    }


@router.get("/status")
def status():
    """Is the model file there?"""
    return {"model_file": MODEL_PATH.name, "ready": MODEL_PATH.exists()}
