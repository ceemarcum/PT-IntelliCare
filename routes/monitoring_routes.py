"""
Monitoring endpoints:
  GET /monitoring/health    quick "is the app up" check (for Google's uptime check)
  GET /monitoring/summary   error rates, user engagement and model performance in one place

Only totals and averages are shown, never anyone's personal data.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database_session import get_db
from monitoring import metrics as M
from models.claim_model import InsuranceClaim
from models.claim_analysis_model import ClaimAnalysis
from models.injury_model import InjuryLog
from models.pain_model import PainScore
from models.progression_model import EngineNotification, ProgressionState
from models.user_model import User

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

SEVERITY_SCALE = {"Not severe at all": 1, "Mild": 3, "Moderate": 5, "Severe": 7, "Very severe": 9}
EXPECTED_ANOMALY_RATE = 5      # % (the threshold is the 95th percentile of the training data)


def pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


def avg(values):
    return round(sum(values) / len(values), 2) if values else None


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return {
        "app_started": M.STARTED_AT.isoformat(timespec="seconds"),
        "note": "Request and model counts are since the app started. Engagement comes from the database.",
        "error_rates": error_rates(),
        "user_engagement": user_engagement(db),
        "model_performance": model_performance(db),
    }


def error_rates():
    total = sum(M.status_counts.values())
    return {
        "requests": total,
        "by_status": dict(M.status_counts),
        "server_error_rate_pct": pct(M.status_counts["5xx"], total),
        "client_error_rate_pct": pct(M.status_counts["4xx"], total),
        "latency_ms": {"p50": M.percentile(M.latencies_ms, 50), "p95": M.percentile(M.latencies_ms, 95)},
        "errors_by_endpoint": dict(M.errors_by_path.most_common(10)),
        "recent_errors": list(M.recent_errors),
    }


def user_engagement(db):
    since = datetime.utcnow() - timedelta(days=7)
    active = (db.query(func.count(func.distinct(PainScore.user_id)))
              .filter(PainScore.timestamp >= since, PainScore.user_id.isnot(None)).scalar())
    checkins = db.query(PainScore).filter(PainScore.timestamp >= since).count()
    per_day = (db.query(func.date(PainScore.timestamp), func.count())
               .filter(PainScore.timestamp >= since).group_by(func.date(PainScore.timestamp)).all())
    levels = db.query(ProgressionState.level, func.count()).group_by(ProgressionState.level).all()
    return {
        "users_total": db.query(User).count(),
        "new_users_7d": db.query(User).filter(User.created_at >= since).count(),
        "active_users_7d": active,
        "checkins_7d": checkins,
        "checkins_per_active_user_7d": round(checkins / active, 1) if active else None,
        "checkins_per_day": {str(day): n for day, n in per_day},
        "injuries_reported_7d": db.query(InjuryLog).filter(InjuryLog.date_reported >= since).count(),
        "plan_updates_7d": db.query(EngineNotification).filter(EngineNotification.created_at >= since).count(),
        "users_by_exercise_level": {level: n for level, n in levels},
        "insurance_claims": db.query(InsuranceClaim).count(),
    }


def model_performance(db):
    return {
        "recovery_model": recovery_model(db),
        "autoencoder": autoencoder(),
        "rag": rag(),
        "recommendation_engine": {"decisions": dict(M.engine_decisions)},
    }


def recovery_model(db):
    preds = list(M.recovery_predictions)
    result = {"predictions": len(preds), "avg_predicted_weeks": avg([p["weeks"] for p in preds])}

    # Drift: are the people using the app like the people the model learned from?
    try:
        from insurance.analytics import load_history
        hist = load_history()
        train_age, train_pain = round(float(hist.Age.mean()), 1), round(float(hist.pain_severity.mean()), 1)
        live_age = avg([p["age"] for p in preds])
        live_pain = avg([SEVERITY_SCALE[p["pain_severity"]] for p in preds])
        result["drift"] = {
            "training_avg_age": train_age, "live_avg_age": live_age,
            "training_avg_pain": train_pain, "live_avg_pain": live_pain,
            "status": ("not enough data" if len(preds) < 20 else
                       "check: users differ from the training data"
                       if abs(live_age - train_age) > 10 or abs(live_pain - train_pain) > 2 else "ok"),
        }
    except FileNotFoundError:
        result["drift"] = {"status": "historical_recovery.csv not found"}

    # Accuracy: once claims have a real recovery time, compare it with what the model predicted
    rows = (db.query(InsuranceClaim.actual_recovery_weeks, ClaimAnalysis.predicted_weeks)
            .join(ClaimAnalysis, ClaimAnalysis.claim_id == InsuranceClaim.id)
            .filter(InsuranceClaim.actual_recovery_weeks.isnot(None), ClaimAnalysis.predicted_weeks.isnot(None)).all())
    result["accuracy_on_finished_claims"] = (
        {"claims": len(rows), "mean_abs_error_weeks": avg([abs(a - p) for a, p in rows])} if rows
        else {"claims": 0, "note": "No claims with an actual recovery time yet."})
    return result


def autoencoder():
    checks = list(M.anomaly_checks)
    flagged = sum(c["is_anomaly"] for c in checks)
    rate = pct(flagged, len(checks))
    return {
        "checks": len(checks),
        "anomalies": flagged,
        "anomaly_rate_pct": rate,
        "expected_rate_pct": EXPECTED_ANOMALY_RATE,
        "avg_reconstruction_error": round(sum(c["error"] for c in checks) / len(checks), 4) if checks else None,
        "status": ("not enough data" if len(checks) < 20 else
                   "check: far more anomalies than expected" if rate > 3 * EXPECTED_ANOMALY_RATE else "ok"),
    }


def rag():
    calls = list(M.rag_calls)
    failures = sum(not c["ok"] for c in calls)
    seconds = [c["seconds"] for c in calls if c["ok"]]
    return {
        "calls": len(calls),
        "failures": failures,
        "failure_rate_pct": pct(failures, len(calls)),
        "avg_seconds": avg(seconds),
        "p95_seconds": M.percentile(seconds, 95),
        "safety_warnings_added": sum(c["safety_warning"] for c in calls),
    }