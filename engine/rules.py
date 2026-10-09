"""
Dynamic exercise recommendation rules (no database or models here, so they're easy to test).

Decision order (safety first):
  1. Autoencoder flags an unusual profile  -> PAUSE: keep the level, notify the user
  2. Latest pain is 8/10 or higher          -> back to BEGINNER, notify
  3. Pain trend increasing                  -> REVERT to BEGINNER, notify
  4. Fewer than 4 check-ins                 -> HOLD until there's enough to see a trend
  5. Pain decreasing (mobility not worse),
     or pain stable + mobility improving
     + pain 4/10 or lower                   -> PROGRESS one level, notify
     (only after 3+ new check-ins at the current level, so users don't jump levels too fast)
  6. Anything else                          -> HOLD at the current level
"""
LEVELS = ["beginner", "intermediate", "advanced"]
MIN_CHECKINS = 4          # need at least this many check-ins to see a trend
TREND_CHANGE = 1.0        # change of 1+ point (0-10 scale) counts as going up or down
HIGH_PAIN = 8
CHECKINS_BEFORE_NEXT_LEVEL = 3   # new check-ins needed at a level before moving up again


def trend(values: list[float]) -> str:
    """Compare the average of the last 3 check-ins with the 3 before them."""
    if len(values) < MIN_CHECKINS:
        return "not_enough_data"
    recent = values[-3:]
    earlier = values[-6:-3]
    change = sum(recent) / len(recent) - sum(earlier) / len(earlier)
    if change <= -TREND_CHANGE:
        return "decreasing"
    if change >= TREND_CHANGE:
        return "increasing"
    return "stable"


def pain_to_severity(score: float) -> str:
    """Convert a 0-10 check-in score to the survey answer the autoencoder and recovery model expect."""
    if score <= 1:
        return "Not severe at all"
    if score <= 3:
        return "Mild"
    if score <= 5:
        return "Moderate"
    if score <= 7:
        return "Severe"
    return "Very severe"


def decide(current_level: str, pain_trend: str, mobility_trend: str,
           is_anomaly: bool | None, latest_pain: float, checkins_at_level: int = CHECKINS_BEFORE_NEXT_LEVEL) -> dict:
    """checkins_at_level: check-ins logged since the level last changed."""
    level = current_level if current_level in LEVELS else "beginner"
    idx = LEVELS.index(level)

    def result(decision, new_level, reasons, notification=None):
        return {"decision": decision, "level_before": level, "level_after": new_level,
                "reasons": reasons, "notification": notification}

    if is_anomaly:
        return result("pause", level,
                      ["The autoencoder flagged your pain profile as unusual compared with similar people."],
                      "Your progression is paused because your recovery profile looks unusual. "
                      "Keep doing your current exercises and check in with your physical therapist.")

    if latest_pain >= HIGH_PAIN:
        return result("regress" if level != "beginner" else "hold", "beginner",
                      [f"Your latest pain is {latest_pain:g}/10, which is high."],
                      "Your pain is high, so your plan is set to beginner exercises. "
                      "If it doesn't ease, see a doctor or physical therapist.")

    if pain_trend == "increasing":
        return result("regress" if level != "beginner" else "hold", "beginner",
                      ["Your pain has been going up over your recent check-ins."],
                      None if level == "beginner" else
                      "Your pain has been increasing, so your plan is back to beginner exercises.")

    if pain_trend == "not_enough_data":
        return result("hold", level, [f"Log at least {MIN_CHECKINS} check-ins so your pain trend can be measured."])

    pain_better = pain_trend == "decreasing" and mobility_trend != "decreasing"
    mobility_better = pain_trend == "stable" and mobility_trend == "increasing" and latest_pain <= 4
    if pain_better or mobility_better:
        reasons = (["Your pain has been going down"] if pain_better else ["Your pain is steady and low"])
        reasons[0] += " and your mobility is improving." if mobility_trend == "increasing" else "."
        if idx == len(LEVELS) - 1:
            return result("hold", level, reasons + ["You're already at the advanced level."])
        if checkins_at_level < CHECKINS_BEFORE_NEXT_LEVEL:
            needed = CHECKINS_BEFORE_NEXT_LEVEL - checkins_at_level
            return result("hold", level, reasons + [f"Log {needed} more check-in(s) at {level} level before moving up."])
        new_level = LEVELS[idx + 1]
        return result("progress", new_level, reasons,
                      f"Great progress! You've moved up to {new_level} exercises.")

    reasons = {"stable": "Your pain is steady.", "decreasing": "Your pain is going down, but your mobility dropped."}
    return result("hold", level, [reasons.get(pain_trend, "No clear change yet.")])
