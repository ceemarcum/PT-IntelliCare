"""
Monitoring: counts requests, errors and model results while the app runs.

- The numbers live in memory, so they reset when the app restarts.
- Errors and model results are also written as JSON log lines. On Cloud Run these go to
  Cloud Logging, which keeps the history (filter by jsonPayload.event).
"""
import json
import time
from collections import Counter, deque
from datetime import datetime, timezone

STARTED_AT = datetime.now(timezone.utc)

# ---- Requests and errors ----
status_counts = Counter()              # {"2xx": 120, "4xx": 3, "5xx": 0}
errors_by_path = Counter()             # server errors (5xx) per endpoint
latencies_ms = deque(maxlen=2000)      # most recent request times
recent_errors = deque(maxlen=20)

# ---- Models (the most recent 1000 results of each) ----
recovery_predictions = deque(maxlen=1000)
anomaly_checks = deque(maxlen=1000)
rag_calls = deque(maxlen=1000)
engine_decisions = Counter()           # {"progress": 3, "hold": 5, ...}

# Pages and files that aren't API calls
SKIP = ("/app", "/docs", "/openapi.json", "/favicon", "/monitoring")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_event(event, severity="INFO", **fields):
    """One JSON line. Cloud Logging reads "severity" and keeps the rest as searchable fields."""
    print(json.dumps({"severity": severity, "event": event, **fields}, default=str), flush=True)


async def track_requests(request, call_next):
    """Middleware: times every API request and counts its status code."""
    path = request.url.path
    if path == "/" or path.startswith(SKIP):
        return await call_next(request)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:                     # a crash becomes a 500 for the user
        _record_request(request.method, path, 500, start, repr(exc))
        raise
    _record_request(request.method, path, response.status_code, start)
    return response


def _record_request(method, path, status, start, error=None):
    ms = round((time.perf_counter() - start) * 1000, 1)
    status_counts[f"{status // 100}xx"] += 1
    latencies_ms.append(ms)
    if status >= 500:
        errors_by_path[path] += 1
        recent_errors.append({"time": now(), "method": method, "path": path, "status": status, "error": error})
        log_event("server_error", "ERROR", method=method, path=path, status=status, ms=ms, error=error)


# ---- Called by the model endpoints ----
def record_recovery(age, pain_severity, exercise_frequency, weeks):
    recovery_predictions.append({"age": age, "pain_severity": pain_severity, "weeks": weeks})
    log_event("recovery_prediction", age=age, pain_severity=pain_severity,
              exercise_frequency=exercise_frequency, weeks=weeks)


def record_anomaly(age, pain_severity, exercise_frequency, error, is_anomaly):
    anomaly_checks.append({"error": error, "is_anomaly": bool(is_anomaly)})
    log_event("anomaly_check", "WARNING" if is_anomaly else "INFO", age=age, pain_severity=pain_severity,
              exercise_frequency=exercise_frequency, reconstruction_error=error, is_anomaly=bool(is_anomaly))


def record_rag(ok, seconds, safety_warning=False, error=None):
    rag_calls.append({"ok": ok, "seconds": seconds, "safety_warning": bool(safety_warning)})
    log_event("rag_guidance", "INFO" if ok else "ERROR", ok=ok, seconds=seconds,
              safety_warning=bool(safety_warning), error=error)


def record_decision(decision):
    engine_decisions[decision] += 1
    log_event("engine_decision", decision=decision)


def percentile(values, pct):
    """Value below which pct% of the numbers fall (None if there are none)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))]