"""
Demo data for the Insurance Analytics module: two patients whose claims were filed 6 weeks ago,
with check-ins spread over those weeks, so the weekly trend graphs have something to show.

  Patient A (demo.ontrack@example.com): pain drops steadily, checks in about 3 times a week
  Patient B (demo.slow@example.com):    pain barely improves, checks in about once a week

Run from the Capstone_Backend folder:  py -m insurance.demo_seed
Running it again replaces the demo patients' check-ins and claims (it doesn't touch other users).
"""
from datetime import datetime, timedelta

import main  # noqa: F401  (loads every model and creates the tables)
from auth.hashing import hash_password
from database import SessionLocal
from models.claim_model import InsuranceClaim
from models.claim_analysis_model import ClaimAnalysis
from models.injury_model import InjuryLog
from models.pain_model import PainScore
from models.user_model import User

WEEKS_AGO = 6

PATIENTS = [
    {"email": "demo.ontrack@example.com", "name": "Demo On Track", "injury": "knee", "symptoms": "stiffness",
     "expected_weeks": 6,
     # (days after the claim, pain, mobility)
     "checkins": [(0, 7, 4), (2, 7, 4), (4, 6, 5), (7, 6, 5), (9, 5, 6), (11, 5, 6), (14, 4, 6), (16, 4, 7),
                  (18, 4, 7), (21, 3, 7), (23, 3, 8), (25, 3, 8), (28, 2, 8), (30, 2, 8), (32, 2, 9),
                  (35, 2, 9), (37, 1, 9), (39, 1, 9)]},
    {"email": "demo.slow@example.com", "name": "Demo Slow", "injury": "lower back", "symptoms": "sharp pain",
     "expected_weeks": 5,
     "checkins": [(0, 7, 4), (6, 7, 4), (13, 6, 4), (20, 7, 3), (27, 6, 4), (34, 6, 4), (40, 7, 3)]},
]


def seed():
    db = SessionLocal()
    claim_date = datetime.utcnow() - timedelta(weeks=WEEKS_AGO)
    try:
        for p in PATIENTS:
            user = db.query(User).filter(User.email == p["email"]).first()
            if not user:
                user = User(email=p["email"], full_name=p["name"], hashed_password=hash_password("demo1234"))
                db.add(user)
                db.flush()
            # start fresh for this demo user
            old_claims = db.query(InsuranceClaim).filter(InsuranceClaim.user_id == user.id).all()
            for c in old_claims:
                db.query(ClaimAnalysis).filter(ClaimAnalysis.claim_id == c.id).delete()
                db.delete(c)
            db.query(PainScore).filter(PainScore.user_id == user.id).delete()
            db.query(InjuryLog).filter(InjuryLog.user_id == user.id).delete()

            db.add(InjuryLog(user_id=user.id, injury_type=p["injury"], symptoms=p["symptoms"],
                             pain_level=p["checkins"][0][1], date_reported=claim_date - timedelta(days=1)))
            claim = InsuranceClaim(user_id=user.id, injury_type=p["injury"], claim_date=claim_date,
                                   expected_recovery_weeks=p["expected_weeks"], flagged=False)
            db.add(claim)
            for day, pain, mobility in p["checkins"]:
                db.add(PainScore(user_id=user.id, score=pain, mobility=mobility, notes="demo",
                                 timestamp=claim_date + timedelta(days=day, hours=1)))
            db.commit()
            print(f"{p['name']}: user_id {user.id}, claim_id {claim.id}, {len(p['checkins'])} check-ins")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
