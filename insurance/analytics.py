"""
Insurance Analytics (Step 6): the calculations, with no database or web code so they're easy to test.

  - Historical comparison: patients like this one in data/historical_recovery.csv
  - Expected recovery curve: how pain should drop if they recover like those patients
  - Recovery tracking: weekly average pain since the claim date
  - Predictive timeline: recovery model (Linear Regression) estimate + a projection from the user's own trend
  - PT utilization: check-ins per week (a stand-in for therapy engagement)
  - Risk classification and the early-intervention flag
"""
import math
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "historical_recovery.csv"

RECOVERED_PAIN = 2          # pain at or below this counts as recovered
TARGET_CHECKINS_PER_WEEK = 3
MIN_SIMILAR = 30            # widen the search until at least this many similar patients are found
BEHIND_BY = 1.5             # pain this far above the expected curve = trending slower than expected


@lru_cache(maxsize=1)
def load_history() -> pd.DataFrame:
    if not HISTORY_PATH.exists():
        raise FileNotFoundError("data/historical_recovery.csv not found. Run the save cell in recovery_rf.ipynb.")
    return pd.read_csv(HISTORY_PATH)


def similar_patients(age: float, pain_severity: float, exercise_level: int) -> dict:
    """Recovery times of historical patients with a similar age, pain and exercise level."""
    df = load_history()
    for age_gap, pain_gap in [(5, 1.5), (10, 2), (15, 3), (100, 10)]:
        match = df[(df.Age.sub(age).abs() <= age_gap)
                   & (df.pain_severity.sub(pain_severity).abs() <= pain_gap)
                   & (df.exercise_level == exercise_level)]
        if len(match) >= MIN_SIMILAR:
            break
    if len(match) < MIN_SIMILAR:   # very rare profile: fall back to everyone
        match = df
    weeks = match.recovery_weeks
    return {
        "n_patients": int(len(match)),
        "median_weeks": round(float(weeks.median()), 1),
        "p25_weeks": round(float(weeks.quantile(0.25)), 1),
        "p75_weeks": round(float(weeks.quantile(0.75)), 1),
        "matched_on": f"age within {age_gap}, pain within {pain_gap}, same exercise level",
    }


def expected_pain(start_pain: float, recovery_weeks: float, week: float) -> float:
    """Pain drops smoothly from start_pain to RECOVERED_PAIN by recovery_weeks (exponential decay)."""
    if start_pain <= RECOVERED_PAIN or recovery_weeks <= 0:
        return float(start_pain)
    k = math.log(start_pain / RECOVERED_PAIN) / recovery_weeks
    return round(max(start_pain * math.exp(-k * week), 0), 2)


def weekly_progress(checkins: list, claim_date: datetime) -> list[dict]:
    """Average pain and mobility per week since the claim. checkins: objects with score, mobility, timestamp."""
    weeks = {}
    for c in checkins:
        if c.timestamp < claim_date:
            continue
        w = int((c.timestamp - claim_date).days // 7)
        weeks.setdefault(w, []).append(c)
    return [{"week": w,
             "avg_pain": round(float(np.mean([c.score for c in rows])), 1),
             "avg_mobility": round(float(np.mean([c.mobility for c in rows])), 1),
             "checkins": len(rows)}
            for w, rows in sorted(weeks.items())]


def project_recovery_week(weekly: list[dict]) -> float | None:
    """Fit the user's weekly pain (log scale) to a straight line and see when it reaches RECOVERED_PAIN."""
    if len(weekly) < 2:
        return None
    x = np.array([w["week"] + 0.5 for w in weekly])          # middle of each week
    y = np.log(np.clip([w["avg_pain"] for w in weekly], 0.5, None))
    slope, intercept = np.polyfit(x, y, 1)
    if slope >= -0.01:      # not improving
        return None
    week = (math.log(RECOVERED_PAIN) - intercept) / slope
    return round(max(week, x[-1]), 1)


def utilization(weekly: list[dict], weeks_since_claim: float) -> dict:
    """Check-ins per week compared with the target. Full weeks only, plus the current partial week."""
    n_weeks = max(math.ceil(weeks_since_claim), 1)
    counts = {w["week"]: w["checkins"] for w in weekly}
    per_week = [counts.get(i, 0) for i in range(n_weeks)]
    total = sum(per_week)
    rate = total / max(weeks_since_claim, 1)
    return {
        "checkins_per_week": per_week,
        "average_per_week": round(rate, 1),
        "target_per_week": TARGET_CHECKINS_PER_WEEK,
        "engagement_pct": round(min(rate / TARGET_CHECKINS_PER_WEEK, 1) * 100),
        "weeks_with_no_checkins": sum(1 for c in per_week if c == 0),
        "note": "Based on app check-ins, used as a stand-in for therapy sessions (no PT attendance data yet).",
    }


def classify_risk(*, is_anomaly, pain_trend, predicted_weeks, similar, weeks_since_claim,
                  insurer_expected_weeks, latest_pain, behind_expected, engagement_pct) -> dict:
    """Points system: 0-1 low, 2-3 medium, 4+ high."""
    points, reasons = 0, []

    def add(n, why):
        nonlocal points
        points += n
        reasons.append(why)

    if is_anomaly:
        add(2, "The autoencoder flagged this pain profile as unusual.")
    if pain_trend == "increasing":
        add(1, "Pain has been going up over recent check-ins.")
    if predicted_weeks and predicted_weeks > similar["p75_weeks"]:
        add(1, f"Predicted recovery ({predicted_weeks} weeks) is slower than most similar patients "
               f"({similar['p75_weeks']} weeks).")
    past_expected = bool(insurer_expected_weeks) and weeks_since_claim > insurer_expected_weeks
    if past_expected and latest_pain is not None and latest_pain > 3:
        add(2, f"Past the expected {insurer_expected_weeks} weeks and pain is still {latest_pain:g}/10.")
    if behind_expected:
        add(1, "Pain is higher than expected for this point in recovery.")
    if engagement_pct is not None and engagement_pct < 50:
        add(1, f"Low engagement: {engagement_pct}% of the target check-ins.")

    level = "high" if points >= 4 else "medium" if points >= 2 else "low"
    early_intervention = (level == "high" or bool(is_anomaly)
                          or (past_expected and latest_pain is not None and latest_pain > 3))
    return {"risk_level": level, "risk_score": points, "reasons": reasons or ["No risk factors found."],
            "needs_early_intervention": early_intervention}


def insights(*, injury_type, similar, status, predicted_weeks, projected_week, weeks_since_claim,
             utilization_info, risk, latest_pain=None) -> list[str]:
    out = [f"Patients like you recover in about {similar['median_weeks']:.0f} weeks "
           f"(most take {similar['p25_weeks']:.0f} to {similar['p75_weeks']:.0f} weeks, "
           f"based on {similar['n_patients']} similar patients)."]
    if status == "slower":
        out.append("Your recovery is trending slower than expected.")
    elif status == "faster":
        out.append("Your recovery is trending faster than expected.")
    elif status == "on_track":
        out.append("Your recovery is on track.")
    if predicted_weeks:
        out.append(f"The recovery model estimates about {predicted_weeks:.0f} weeks for your {injury_type} injury.")
    if latest_pain is not None and latest_pain <= RECOVERED_PAIN:
        out.append(f"Pain is down to {latest_pain:g}/10, so you've reached the recovered range after "
                   f"{weeks_since_claim:.0f} weeks.")
    elif projected_week:
        left = max(projected_week - weeks_since_claim, 0)
        out.append(f"At your current rate, you should reach low pain in about {left:.0f} more week(s).")
    if utilization_info["engagement_pct"] < 50:
        out.append(f"You're checking in {utilization_info['average_per_week']} times a week; "
                   f"the goal is {TARGET_CHECKINS_PER_WEEK}.")
    if risk["needs_early_intervention"]:
        out.append("This case is flagged for early intervention (a care manager or PT follow-up).")
    return out


def recovery_status(latest_week: dict | None, expected_now: float | None) -> str:
    if not latest_week or expected_now is None:
        return "not_enough_data"
    diff = latest_week["avg_pain"] - expected_now
    if diff > BEHIND_BY:
        return "slower"
    if diff < -BEHIND_BY:
        return "faster"
    return "on_track"


def date_after(start: datetime, weeks: float | None) -> str | None:
    return None if weeks is None else (start + timedelta(weeks=weeks)).date().isoformat()
