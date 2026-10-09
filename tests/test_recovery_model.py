"""
Recovery time model (Linear Regression, linear_regression/recovery_lr.joblib).
Validates: "Recovery predictions are reasonable."
"""
import numpy as np
import pandas as pd
import pytest

from routes import recovery_routes as R
from routes.recovery_routes import PatientProfile, predict_recovery, SEVERITY_MAP, EXERCISE_MAP, FEATURES
from insurance.analytics import similar_patients

SEVERITIES = ["Not severe at all", "Mild", "Moderate", "Severe", "Very severe"]
EXERCISE = ["I do not exercise at all.", "I exercise sometimes.", "I exercise most of the time.", "I always exercise."]


def weeks(age=30, pain="Moderate", exercise="I exercise sometimes."):
    return predict_recovery(PatientProfile(age=age, pain_severity=pain, exercise_frequency=exercise))


def test_known_patient():
    """Age 30, severe pain, exercises sometimes: about 8.3 weeks (checked in /docs)."""
    r = weeks(30, "Severe")
    assert r["predicted_recovery_weeks"] == pytest.approx(8.3, abs=0.15)
    assert r["model"] == "linear_regression"


def test_more_pain_means_longer_recovery():
    preds = [weeks(pain=p)["predicted_recovery_weeks"] for p in SEVERITIES]
    assert preds == sorted(preds) and preds[-1] > preds[0]


def test_more_exercise_means_faster_recovery():
    preds = [weeks(exercise=e)["predicted_recovery_weeks"] for e in EXERCISE]
    assert preds == sorted(preds, reverse=True) and preds[0] > preds[-1]


def test_older_means_longer_recovery():
    assert weeks(age=60)["predicted_recovery_weeks"] > weeks(age=20)["predicted_recovery_weeks"]


@pytest.mark.parametrize("pain", SEVERITIES)
@pytest.mark.parametrize("exercise", EXERCISE)
def test_predictions_stay_in_a_sensible_range(pain, exercise):
    r = weeks(25, pain, exercise)
    low, high = r["likely_range_weeks"]
    assert 2 <= r["predicted_recovery_weeks"] <= 30          # the simulation's limits
    assert low <= r["predicted_recovery_weeks"] <= high
    assert low >= 2


def test_likely_range_covers_about_80_percent_of_patients():
    """The 'likely range' should contain about 80% of the historical patients' real recovery times."""
    model = R._load()
    hist = pd.read_csv(R.HISTORY_PATH)
    pred = model.predict(hist[FEATURES])
    margin = R.Z_80 * R._typical_error
    inside = np.mean((hist["recovery_weeks"] >= pred - margin) & (hist["recovery_weeks"] <= pred + margin))
    assert 0.75 <= inside <= 0.85


@pytest.mark.parametrize("age,pain,exercise", [
    (22, "Moderate", "I exercise sometimes."),
    (30, "Severe", "I exercise sometimes."),
    (25, "Mild", "I always exercise."),
    (24, "Very severe", "I never exercise regularly."),
])
def test_prediction_close_to_similar_patients(age, pain, exercise):
    """Within 2 weeks of the median for similar historical patients (ages 18-30, where most of the data is)."""
    pred = weeks(age, pain, exercise)["predicted_recovery_weeks"]
    similar = similar_patients(age, SEVERITY_MAP[pain], EXERCISE_MAP[exercise])
    assert abs(pred - similar["median_weeks"]) <= 2.0
