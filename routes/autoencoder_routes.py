"""
Autoencoder endpoint: checks whether a user's pain profile is unusual.

Loads the model trained in autoencoder/preprocess.ipynb:
  autoencoder/recovery_autoencoder_weights.npz  learned weights, exported from recovery_autoencoder.weights.h5
                                                by autoencoder/export_weights.py
  autoencoder/autoencoder_scaler.joblib         MinMaxScaler fitted on the training data
  autoencoder/autoencoder_threshold.joblib      95th percentile of the training reconstruction errors

The mappings, column order and model class below must match the notebook exactly.
If you change them there, change them here too.

The model runs with NumPy instead of TensorFlow: Windows Smart App Control blocks TensorFlow's DLLs, and this
small network (3 -> 4 -> 2 -> 4 -> 3) is just four matrix multiplications. It gives the same results as
the Keras model (checked to within 0.0000001). After retraining, run:  py -m autoencoder.export_weights
"""
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from monitoring.metrics import record_anomaly

router = APIRouter(prefix="/autoencoder", tags=["Autoencoder"])

MODEL_DIR = Path(__file__).resolve().parent.parent / "autoencoder"
WEIGHTS_PATH = MODEL_DIR / "recovery_autoencoder_weights.npz"
SCALER_PATH = MODEL_DIR / "autoencoder_scaler.joblib"
THRESHOLD_PATH = MODEL_DIR / "autoencoder_threshold.joblib"

# Same as the notebook
SEVERITY_MAP = {"Not severe at all": 1, "Mild": 3, "Moderate": 5, "Severe": 7, "Very severe": 9}
EXERCISE_MAP = {"I never exercise regularly.": 0, "I do not exercise at all.": 0,
                "I exercise sometimes.": 1, "I exercise most of the time.": 2, "I always exercise.": 3}
N_FEATURES = 3   # Age, pain_severity, exercise_level (in that order)

_model, _scaler, _threshold = None, None, None


def _relu(z):
    return np.maximum(z, 0)


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


class AnomalyDetector:
    """Same layers as the notebook's AnomalyDetector class, run with NumPy:
    encoder Dense(4, relu) -> Dense(2, relu), decoder Dense(4, relu) -> Dense(3, sigmoid)."""

    def __init__(self, weights):
        self.w = weights

    def predict(self, x):
        w = self.w
        h = _relu(x @ w["W0"] + w["b0"])        # encoder
        h = _relu(h @ w["W1"] + w["b1"])
        h = _relu(h @ w["W2"] + w["b2"])        # decoder
        return _sigmoid(h @ w["W3"] + w["b3"])


def _load():
    """Load the model, scaler and threshold once, on the first request."""
    global _model, _scaler, _threshold
    if _model is None:
        missing = [p.name for p in (WEIGHTS_PATH, SCALER_PATH, THRESHOLD_PATH) if not p.exists()]
        if missing:
            raise HTTPException(status_code=503,
                                detail=f"Autoencoder files missing in the autoencoder folder: {', '.join(missing)}. "
                                       "Run the save cell in preprocess.ipynb, then: py -m autoencoder.export_weights")
        import joblib
        with np.load(WEIGHTS_PATH) as data:
            model = AnomalyDetector({k: data[k] for k in data.files})
        _scaler = joblib.load(SCALER_PATH)
        _threshold = float(joblib.load(THRESHOLD_PATH))
        _model = model
    return _model, _scaler, _threshold


class PainProfile(BaseModel):
    age: float = Field(ge=1, le=120, examples=[22])
    pain_severity: Literal["Not severe at all", "Mild", "Moderate", "Severe", "Very severe"] = Field(
        examples=["Moderate"])
    exercise_frequency: Literal["I never exercise regularly.", "I do not exercise at all.", "I exercise sometimes.",
                                "I exercise most of the time.", "I always exercise."] = Field(
        examples=["I exercise sometimes."])


@router.post("/check")
def check_profile(profile: PainProfile):
    """Is this pain profile unusual compared with the survey group?"""
    model, scaler, threshold = _load()

    # Same steps as the notebook: map text to numbers -> scale -> rebuild -> error
    row = np.array([[profile.age, SEVERITY_MAP[profile.pain_severity],
                     EXERCISE_MAP[profile.exercise_frequency]]], dtype="float32")
    scaled = scaler.transform(row).astype("float32")
    rebuilt = model.predict(scaled)
    error = float(np.mean(np.abs(rebuilt - scaled)))

    is_anomaly = error > threshold

    record_anomaly(profile.age, profile.pain_severity, profile.exercise_frequency, round(error, 4), is_anomaly)
    
    return {
        "is_anomaly": is_anomaly,
        "message": ("This pain profile is unusual compared with the survey group."
                    if is_anomaly else "This pain profile is typical of the survey group."),
        "reconstruction_error": round(error, 4),
        "threshold": round(threshold, 4),
    }


@router.get("/status")
def status():
    """Are the model files there, and what threshold is in use?"""
    files = {p.name: p.exists() for p in (WEIGHTS_PATH, SCALER_PATH, THRESHOLD_PATH)}
    result = {"files": files, "ready": all(files.values())}
    if result["ready"]:
        import joblib
        result["threshold"] = round(float(joblib.load(THRESHOLD_PATH)), 4)
    return result
