"""Run from the Capstone_Backend folder:  py -m pytest tests"""
from engine.rules import trend, decide, pain_to_severity


def test_trend():
    assert trend([7, 7, 6]) == "not_enough_data"
    assert trend([7, 7, 6, 5, 4, 4]) == "decreasing"
    assert trend([3, 3, 4, 5, 6, 6]) == "increasing"
    assert trend([5, 5, 5, 5, 6, 5]) == "stable"


def test_pain_decreasing_progresses():
    r = decide("beginner", "decreasing", "increasing", False, 3)
    assert r["decision"] == "progress" and r["level_after"] == "intermediate" and r["notification"]


def test_pain_increasing_reverts_to_beginner():
    r = decide("intermediate", "increasing", "stable", False, 6)
    assert r["decision"] == "regress" and r["level_after"] == "beginner"


def test_anomaly_pauses_even_if_pain_improves():
    r = decide("intermediate", "decreasing", "increasing", True, 3)
    assert r["decision"] == "pause" and r["level_after"] == "intermediate" and r["notification"]


def test_high_pain_goes_to_beginner():
    r = decide("advanced", "stable", "stable", False, 9)
    assert r["level_after"] == "beginner"


def test_not_enough_data_holds():
    r = decide("beginner", "not_enough_data", "not_enough_data", False, 5)
    assert r["decision"] == "hold"


def test_advanced_stays_advanced():
    r = decide("advanced", "decreasing", "increasing", False, 2)
    assert r["decision"] == "hold" and r["level_after"] == "advanced"


def test_pain_to_severity():
    assert pain_to_severity(0) == "Not severe at all"
    assert pain_to_severity(6) == "Severe"
    assert pain_to_severity(10) == "Very severe"


def test_waits_for_new_checkins_before_next_level():
    r = decide("intermediate", "decreasing", "increasing", False, 3, checkins_at_level=1)
    assert r["decision"] == "hold" and r["level_after"] == "intermediate"
    r = decide("intermediate", "decreasing", "increasing", False, 3, checkins_at_level=3)
    assert r["level_after"] == "advanced"
