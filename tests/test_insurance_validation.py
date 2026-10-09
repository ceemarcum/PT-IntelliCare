"""
Insurance analytics on two known patients with 6 weeks of history (the same ones as insurance/demo_seed.py):
  on-track: pain 7 -> 1, checks in 3 times a week
  slow:     pain stays 6-7, checks in about once a week, past the insurer's 5-week estimate
Validates: "Insurance analytics are accurate" (results checked against values worked out by hand).
"""
from datetime import datetime, timedelta

import pandas as pd
import pytest

from insurance.analytics import HISTORY_PATH
from insurance.demo_seed import PATIENTS
from models.claim_model import InsuranceClaim
from models.injury_model import InjuryLog
from models.pain_model import PainScore
from models.user_model import User

AGE, EXERCISE = 30, "I exercise sometimes."


@pytest.fixture
def claims(session_factory):
    """Create both demo patients in the test database. Returns {"on_track": claim_id, "slow": claim_id}."""
    db = session_factory()
    claim_date = datetime.utcnow() - timedelta(weeks=6)
    ids = {}
    for key, p in zip(["on_track", "slow"], PATIENTS):
        user = User(email=p["email"], full_name=p["name"], hashed_password="x")
        db.add(user)
        db.flush()
        db.add(InjuryLog(user_id=user.id, injury_type=p["injury"], symptoms=p["symptoms"],
                         pain_level=p["checkins"][0][1], date_reported=claim_date - timedelta(days=1)))
        claim = InsuranceClaim(user_id=user.id, injury_type=p["injury"], claim_date=claim_date,
                               expected_recovery_weeks=p["expected_weeks"], flagged=False)
        db.add(claim)
        for day, pain, mobility in p["checkins"]:
            db.add(PainScore(user_id=user.id, score=pain, mobility=mobility, notes="test",
                             timestamp=claim_date + timedelta(days=day, hours=1)))
        db.commit()
        ids[key] = claim.id
    db.close()
    return ids


def report(client, claim_id):
    r = client.get(f"/insurance/claims/{claim_id}/report", params={"age": AGE, "exercise_frequency": EXERCISE})
    assert r.status_code == 200, r.text
    return r.json()


def test_on_track_patient(client, claims):
    r = report(client, claims["on_track"])
    assert r["risk"]["risk_level"] == "low"
    assert r["flagged_for_early_intervention"] is False
    assert r["recovery_tracking"]["status"] in ("on_track", "faster")
    assert r["recovery_tracking"]["starting_pain"] == 7 and r["recovery_tracking"]["latest_pain"] == 1
    assert r["pt_utilization"]["checkins_per_week"] == [3, 3, 3, 3, 3, 3]
    assert r["pt_utilization"]["engagement_pct"] == 100
    assert r["predictive_timeline"]["projected_weeks_from_your_trend"] is not None   # improving, so it can project


def test_slow_patient(client, claims):
    r = report(client, claims["slow"])
    assert r["risk"]["risk_level"] == "high"
    assert r["flagged_for_early_intervention"] is True
    assert r["recovery_tracking"]["status"] == "slower"
    assert "Your recovery is trending slower than expected." in r["insights"]

    # Worked out by hand: 7 check-ins over 6 weeks = 1.2 a week; 1.2 / 3 target = 39%
    u = r["pt_utilization"]
    assert u["checkins_per_week"] == [2, 1, 1, 1, 1, 1]
    assert u["average_per_week"] == 1.2 and u["engagement_pct"] == 39

    # Risk points: past the 5-week estimate with pain 7 (+2), behind the expected curve (+1), low engagement (+1)
    assert r["risk"]["risk_score"] == 4
    reasons = " ".join(r["risk"]["reasons"])
    assert "Past the expected 5 weeks" in reasons and "Low engagement" in reasons
    assert r["predictive_timeline"]["projected_weeks_from_your_trend"] is None    # not improving


def test_comparison_matches_the_historical_data(client, claims):
    """'Patients like you' numbers match a direct calculation on historical_recovery.csv."""
    r = report(client, claims["slow"])
    hist = pd.read_csv(HISTORY_PATH)
    # starting pain 7 -> "Severe" -> 7 on the survey scale; age 30; "sometimes" -> exercise level 1
    similar = hist[(hist.Age.sub(30).abs() <= 5) & (hist.pain_severity.sub(7).abs() <= 1.5) & (hist.exercise_level == 1)]
    h = r["historical_comparison"]
    assert h["n_patients"] == len(similar)
    assert h["median_weeks"] == round(similar.recovery_weeks.median(), 1)
    assert h["p25_weeks"] == round(similar.recovery_weeks.quantile(0.25), 1)
    assert h["p75_weeks"] == round(similar.recovery_weeks.quantile(0.75), 1)


def test_flags_and_portfolio(client, claims, session_factory):
    report(client, claims["on_track"])
    report(client, claims["slow"])

    flagged = client.get("/insurance/flagged").json()
    assert [f["claim_id"] for f in flagged] == [claims["slow"]]

    portfolio = client.get("/insurance/portfolio").json()
    assert portfolio["claims_analyzed"] == 2
    assert portfolio["risk_counts"] == {"low": 1, "medium": 0, "high": 1}

    db = session_factory()
    assert db.get(InsuranceClaim, claims["slow"]).flagged is True       # the report updates the claim itself
    assert db.get(InsuranceClaim, claims["on_track"]).flagged is False
    db.close()
