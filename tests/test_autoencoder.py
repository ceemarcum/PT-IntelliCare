"""
Autoencoder anomaly check (trained in TensorFlow in preprocess.ipynb, served with NumPy).
Validates: "Anomaly detection triggers correctly."
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from routes.autoencoder_routes import check_profile, PainProfile, SEVERITY_MAP, EXERCISE_MAP, THRESHOLD_PATH, _load

DATA = Path(__file__).resolve().parent.parent / "data" / "Pain Data.xlsx"

# Reconstruction errors from the original Keras (TensorFlow) model, recorded before switching to NumPy.
KERAS_REFERENCE = [
    (22, "Moderate", "I exercise sometimes.", 0.00252),
    (30, "Mild", "I exercise sometimes.", 0.00393),
    (24, "Severe", "I never exercise regularly.", 0.11714),
    (70, "Very severe", "I always exercise.", 0.30363),
    (60, "Not severe at all", "I always exercise.", 0.27133),
]


def check(age, pain, exercise):
    return check_profile(PainProfile(age=age, pain_severity=pain, exercise_frequency=exercise))


def test_threshold_is_the_one_from_the_notebook():
    assert check(22, "Moderate", "I exercise sometimes.")["threshold"] == pytest.approx(
        float(joblib.load(THRESHOLD_PATH)), abs=1e-4)


@pytest.mark.parametrize("age,pain,exercise,expected", KERAS_REFERENCE)
def test_numpy_matches_the_keras_model(age, pain, exercise, expected):
    assert check(age, pain, exercise)["reconstruction_error"] == pytest.approx(expected, abs=1e-3)


@pytest.mark.parametrize("age,pain,exercise", [
    (22, "Moderate", "I exercise sometimes."),
    (30, "Mild", "I exercise sometimes."),
    (24, "Severe", "I never exercise regularly."),
])
def test_typical_profiles_are_not_flagged(age, pain, exercise):
    r = check(age, pain, exercise)
    assert r["is_anomaly"] is False and "typical" in r["message"]


@pytest.mark.parametrize("age,pain,exercise", [
    (70, "Very severe", "I always exercise."),     # much older than the survey group, extreme answers
    (60, "Not severe at all", "I always exercise."),
])
def test_unusual_profiles_are_flagged(age, pain, exercise):
    r = check(age, pain, exercise)
    assert r["is_anomaly"] is True and r["reconstruction_error"] > r["threshold"]


def test_flags_about_5_percent_of_the_survey():
    """The threshold is the 95th percentile, so about 5% of the survey people should be flagged."""
    df = pd.read_excel(DATA).dropna(subset=["Age"])
    sev = "Rate the severity of your pain (Likert scale) [How severe is your pain now?]"
    ex = "How would you rate yourself based on your exercise frequency?"
    no_pain = df["What is your pain type?"] == "No pain"
    df.loc[no_pain & df[sev].isnull(), sev] = "Not severe at all"   # same cleaning as preprocess.ipynb
    df = df.dropna(subset=[sev])

    model, scaler, threshold = _load()
    X = np.column_stack([df["Age"], df[sev].map(SEVERITY_MAP), df[ex].map(EXERCISE_MAP)]).astype("float32")
    scaled = scaler.transform(X).astype("float32")
    errors = np.mean(np.abs(model.predict(scaled) - scaled), axis=1)
    flagged = np.mean(errors > threshold)
    assert 0.02 <= flagged <= 0.10
