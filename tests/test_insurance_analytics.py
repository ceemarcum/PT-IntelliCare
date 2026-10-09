from datetime import datetime, timedelta
from types import SimpleNamespace

from insurance import analytics as A


def checkin(day, score, mobility=5, start=datetime(2026, 1, 1)):
    return SimpleNamespace(score=score, mobility=mobility, timestamp=start + timedelta(days=day))


def base_risk(**changes):
    args = dict(is_anomaly=False, pain_trend="decreasing", predicted_weeks=6,
                similar={"p75_weeks": 8}, weeks_since_claim=3, insurer_expected_weeks=6,
                latest_pain=4, behind_expected=False, engagement_pct=100)
    args.update(changes)
    return A.classify_risk(**args)


def test_similar_patients_finds_enough():
    s = A.similar_patients(30, 7, 1)
    assert s["n_patients"] >= A.MIN_SIMILAR
    assert s["p25_weeks"] <= s["median_weeks"] <= s["p75_weeks"]


def test_expected_pain_reaches_recovered_at_median():
    assert A.expected_pain(7, 6, 0) == 7
    assert abs(A.expected_pain(7, 6, 6) - A.RECOVERED_PAIN) < 0.01


def test_weekly_progress_groups_by_week_after_claim():
    rows = [checkin(-2, 9), checkin(0, 7), checkin(3, 6), checkin(8, 4)]
    weekly = A.weekly_progress(rows, datetime(2026, 1, 1))
    assert [w["week"] for w in weekly] == [0, 1]       # the check-in before the claim is ignored
    assert weekly[0]["avg_pain"] == 6.5 and weekly[0]["checkins"] == 2


def test_projection_none_when_not_improving():
    flat = [{"week": 0, "avg_pain": 6}, {"week": 1, "avg_pain": 6}, {"week": 2, "avg_pain": 7}]
    assert A.project_recovery_week(flat) is None
    down = [{"week": 0, "avg_pain": 7}, {"week": 1, "avg_pain": 5}, {"week": 2, "avg_pain": 3.5}]
    assert A.project_recovery_week(down) > 2.5


def test_low_risk_when_nothing_wrong():
    r = base_risk()
    assert r["risk_level"] == "low" and not r["needs_early_intervention"]


def test_high_risk_and_flag_when_slow():
    r = base_risk(weeks_since_claim=7, latest_pain=7, behind_expected=True, engagement_pct=30)
    assert r["risk_level"] == "high" and r["risk_score"] == 4 and r["needs_early_intervention"]


def test_anomaly_always_flags():
    r = base_risk(is_anomaly=True)
    assert r["risk_level"] == "medium" and r["needs_early_intervention"]
