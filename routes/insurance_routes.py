from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Literal
from database_session import get_db
from models.claim_model import InsuranceClaim
from models.claim_analysis_model import ClaimAnalysis
from models.injury_model import InjuryLog
from models.pain_model import PainScore

router = APIRouter(prefix="/insurance", tags=["Insurance"])

@router.post("/submit-claim")
def submit_claim(
    user_id: int,
    injury_type: str,
    expected_recovery_weeks: int,
    actual_recovery_weeks: int | None = None,
    db: Session = Depends(get_db)
):
    new_claim = InsuranceClaim(
        user_id=user_id,
        injury_type=injury_type,
        claim_date=datetime.utcnow(),
        expected_recovery_weeks=expected_recovery_weeks,
        actual_recovery_weeks=actual_recovery_weeks,
        flagged=False
    )

    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)

    return {
        "message": "Insurance claim submitted",
        "claim_id": new_claim.id
    }

@router.get("/analytics/{user_id}")
def insurance_analytics(user_id: int, db: Session = Depends(get_db)):
    # Fetch all claims for this user
    claims = db.query(InsuranceClaim).filter(InsuranceClaim.user_id == user_id).all()

    if not claims:
        return {"message": "No claims found for this user"}

    analytics = []

    for claim in claims:
        # Basic recovery status logic
        status = "on-track"
        if claim.actual_recovery_weeks and claim.actual_recovery_weeks > claim.expected_recovery_weeks:
            status = "delayed"

        analytics.append({
            "claim_id": claim.id,
            "injury_type": claim.injury_type,
            "expected_recovery_weeks": claim.expected_recovery_weeks,
            "actual_recovery_weeks": claim.actual_recovery_weeks,
            "status": status
        })

    return {
        "user_id": user_id,
        "analytics": analytics
    }


# ---------------------------------------------------------------------------
# Step 6: Insurance Analytics Module (calculations in insurance/analytics.py)
# ---------------------------------------------------------------------------
ExerciseFrequency = Literal["I never exercise regularly.", "I do not exercise at all.", "I exercise sometimes.",
                            "I exercise most of the time.", "I always exercise."]


def _get_claim(db, claim_id):
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


def _profile(db, claim, age, exercise_frequency):
    """Use the age and exercise answer given, or the ones saved by the last report."""
    if age is None or exercise_frequency is None:
        saved = db.query(ClaimAnalysis).filter(ClaimAnalysis.claim_id == claim.id).first()
        if not saved:
            raise HTTPException(status_code=400,
                                detail="Enter age and exercise_frequency (or run the report once first).")
        age = saved.age if age is None else age
        exercise_frequency = saved.exercise_frequency if exercise_frequency is None else exercise_frequency
    return age, exercise_frequency


def _analyze(db, claim, age, exercise_frequency):
    """Everything the report and charts need for one claim."""
    from insurance import analytics as A
    from engine.rules import trend, pain_to_severity
    from routes.engine_routes import _anomaly, _recovery
    from routes.recovery_routes import SEVERITY_MAP, EXERCISE_MAP

    checkins = (db.query(PainScore).filter(PainScore.user_id == claim.user_id)
                .order_by(PainScore.timestamp).all())
    after_claim = [c for c in checkins if c.timestamp >= claim.claim_date]
    injury = (db.query(InjuryLog).filter(InjuryLog.user_id == claim.user_id)
              .order_by(InjuryLog.date_reported.desc()).first())

    # Starting pain: first check-in after the claim, else the injury report
    if after_claim:
        start_pain = after_claim[0].score
    elif injury:
        start_pain = injury.pain_level
    else:
        raise HTTPException(status_code=404, detail="No check-ins or injury report for this user yet.")
    latest_pain = after_claim[-1].score if after_claim else start_pain

    weeks_since = round((datetime.utcnow() - claim.claim_date).total_seconds() / (7 * 86400), 1)
    weekly = A.weekly_progress(after_claim, claim.claim_date)

    # 1. Compare with historical patients (starting pain, age, exercise)
    try:
        similar = A.similar_patients(age, SEVERITY_MAP[pain_to_severity(start_pain)], EXERCISE_MAP[exercise_frequency])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # 2. Models: recovery model (Linear Regression) from the starting pain, autoencoder from the current pain
    recovery = _recovery(age, pain_to_severity(start_pain), exercise_frequency)
    anomaly = _anomaly(age, pain_to_severity(latest_pain), exercise_frequency)
    predicted = recovery.get("predicted_recovery_weeks")

    # 3. Tracking: where the user is vs the expected curve
    expected_now = (A.expected_pain(start_pain, similar["median_weeks"], weekly[-1]["week"] + 0.5)
                    if weekly else None)
    status = A.recovery_status(weekly[-1] if weekly else None, expected_now)
    projected = A.project_recovery_week(weekly)
    pain_trend = trend([c.score for c in after_claim])
    util = A.utilization(weekly, weeks_since)

    # 4. Risk and early intervention
    risk = A.classify_risk(is_anomaly=anomaly.get("is_anomaly"), pain_trend=pain_trend, predicted_weeks=predicted,
                           similar=similar, weeks_since_claim=weeks_since,
                           insurer_expected_weeks=claim.expected_recovery_weeks, latest_pain=latest_pain,
                           behind_expected=status == "slower", engagement_pct=util["engagement_pct"])

    return {
        "claim": claim, "start_pain": start_pain, "latest_pain": latest_pain, "weeks_since": weeks_since,
        "weekly": weekly, "similar": similar, "recovery": recovery, "anomaly": anomaly, "predicted": predicted,
        "expected_now": expected_now, "status": status, "projected": projected, "pain_trend": pain_trend,
        "util": util, "risk": risk,
        "insights": A.insights(injury_type=claim.injury_type, similar=similar, status=status,
                               predicted_weeks=predicted, projected_week=projected, weeks_since_claim=weeks_since,
                               utilization_info=util, risk=risk, latest_pain=latest_pain),
        "timeline": {
            "claim_date": claim.claim_date.date().isoformat(),
            "weeks_since_claim": weeks_since,
            "insurer_expected_weeks": claim.expected_recovery_weeks,
            "insurer_expected_date": A.date_after(claim.claim_date, claim.expected_recovery_weeks),
            "model_predicted_weeks": predicted,
            "model_likely_range_weeks": recovery.get("likely_range_weeks"),
            "model_expected_date": A.date_after(claim.claim_date, predicted),
            "similar_patients_median_weeks": similar["median_weeks"],
            "projected_weeks_from_your_trend": projected,
            "projected_date_from_your_trend": A.date_after(claim.claim_date, projected),
        },
    }


@router.get("/claims/{claim_id}/report")
def claim_report(claim_id: int, age: float = Query(ge=1, le=120, examples=[30]),
                 exercise_frequency: ExerciseFrequency = Query(examples=["I exercise sometimes."]),
                 db: Session = Depends(get_db)):
    """Recovery tracking, comparison with similar patients, risk, utilization, timeline and insights.
    Also updates the claim's flagged field and saves the result for the portfolio view."""
    claim = _get_claim(db, claim_id)
    r = _analyze(db, claim, age, exercise_frequency)
    risk = r["risk"]

    claim.flagged = risk["needs_early_intervention"]
    saved = db.query(ClaimAnalysis).filter(ClaimAnalysis.claim_id == claim.id).first() or ClaimAnalysis(claim_id=claim.id)
    saved.user_id, saved.injury_type, saved.age, saved.exercise_frequency = (
        claim.user_id, claim.injury_type, age, exercise_frequency)
    saved.risk_level, saved.risk_score, saved.reasons = risk["risk_level"], risk["risk_score"], " | ".join(risk["reasons"])
    saved.recovery_status, saved.predicted_weeks, saved.weeks_since_claim = r["status"], r["predicted"], r["weeks_since"]
    saved.engagement_pct, saved.flagged, saved.analyzed_at = r["util"]["engagement_pct"], claim.flagged, datetime.utcnow()
    db.add(saved)
    db.commit()

    return {
        "claim_id": claim.id,
        "user_id": claim.user_id,
        "injury_type": claim.injury_type,
        "insights": r["insights"],
        "risk": risk,
        "flagged_for_early_intervention": claim.flagged,
        "recovery_tracking": {
            "status": r["status"],
            "starting_pain": r["start_pain"],
            "latest_pain": r["latest_pain"],
            "expected_pain_now": r["expected_now"],
            "pain_trend": r["pain_trend"],
            "weekly": r["weekly"],
        },
        "historical_comparison": r["similar"],
        "predictive_timeline": r["timeline"],
        "pt_utilization": r["util"],
        "anomaly_check": r["anomaly"],
        "charts": {
            "recovery_trend": f"/insurance/claims/{claim.id}/chart/recovery-trend.png",
            "utilization": f"/insurance/claims/{claim.id}/chart/utilization.png",
        },
    }


@router.get("/claims/{claim_id}/chart/recovery-trend.png", response_class=Response)
def recovery_trend_chart(claim_id: int, age: float | None = Query(None, ge=1, le=120),
                         exercise_frequency: ExerciseFrequency | None = None, db: Session = Depends(get_db)):
    """Graph: the user's weekly pain vs the expected curve for similar patients."""
    from insurance import charts
    claim = _get_claim(db, claim_id)
    r = _analyze(db, claim, *_profile(db, claim, age, exercise_frequency))
    png = charts.recovery_trend(r["weekly"], r["start_pain"], r["similar"],
                                title=f"Recovery trend: claim {claim.id} ({claim.injury_type})")
    return Response(content=png, media_type="image/png")


@router.get("/claims/{claim_id}/chart/utilization.png", response_class=Response)
def utilization_chart(claim_id: int, age: float | None = Query(None, ge=1, le=120),
                      exercise_frequency: ExerciseFrequency | None = None, db: Session = Depends(get_db)):
    """Graph: check-ins per week vs the target."""
    from insurance import charts
    claim = _get_claim(db, claim_id)
    r = _analyze(db, claim, *_profile(db, claim, age, exercise_frequency))
    png = charts.utilization(r["util"]["checkins_per_week"], title=f"PT utilization: claim {claim.id}")
    return Response(content=png, media_type="image/png")


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    """All analyzed claims: risk counts, and recovery and utilization patterns by injury type and risk level."""
    rows = db.query(ClaimAnalysis).all()
    if not rows:
        return {"message": "No claims analyzed yet. Run GET /insurance/claims/{claim_id}/report first."}

    def summary(group):
        preds = [g.predicted_weeks for g in group if g.predicted_weeks]
        return {"claims": len(group),
                "avg_predicted_weeks": round(sum(preds) / len(preds), 1) if preds else None,
                "avg_weeks_since_claim": round(sum(g.weeks_since_claim for g in group) / len(group), 1),
                "avg_engagement_pct": round(sum(g.engagement_pct for g in group) / len(group)),
                "flagged": sum(1 for g in group if g.flagged)}

    by_injury, by_risk = {}, {}
    for r in rows:
        by_injury.setdefault(r.injury_type, []).append(r)
        by_risk.setdefault(r.risk_level, []).append(r)
    return {
        "claims_analyzed": len(rows),
        "risk_counts": {lvl: len(by_risk.get(lvl, [])) for lvl in ("low", "medium", "high")},
        "flagged_for_early_intervention": sum(1 for r in rows if r.flagged),
        "by_injury_type": {k: summary(v) for k, v in by_injury.items()},
        "by_risk_level": {k: summary(v) for k, v in by_risk.items()},
        "chart": "/insurance/portfolio/chart/risk.png",
    }


@router.get("/portfolio/chart/risk.png", response_class=Response)
def portfolio_risk_chart(db: Session = Depends(get_db)):
    """Graph: how many analyzed claims are low, medium and high risk."""
    from insurance import charts
    counts = {}
    for r in db.query(ClaimAnalysis).all():
        counts[r.risk_level] = counts.get(r.risk_level, 0) + 1
    return Response(content=charts.risk_distribution(counts), media_type="image/png")


@router.get("/flagged")
def flagged_claims(db: Session = Depends(get_db)):
    """Claims that need early intervention, highest risk first."""
    rows = (db.query(ClaimAnalysis).filter(ClaimAnalysis.flagged == True)  # noqa: E712
            .order_by(ClaimAnalysis.risk_score.desc()).all())
    return [{"claim_id": r.claim_id, "user_id": r.user_id, "injury_type": r.injury_type,
             "risk_level": r.risk_level, "risk_score": r.risk_score, "reasons": r.reasons.split(" | "),
             "recovery_status": r.recovery_status, "analyzed_at": r.analyzed_at} for r in rows]
