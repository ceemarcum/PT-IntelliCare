"""
Full pipeline, end to end, through the real API (test database, fake RAG):
register -> login -> injury -> daily check-ins -> exercise plan -> progress -> claim -> insurance report -> app page.
Validates: "Exercise recommendations make sense" at the system level.
"""
AGE, EXERCISE = 30, "I exercise sometimes."


def register_and_login(client, email):
    r = client.post("/auth/register", json={"email": email, "full_name": "Test Patient", "password": "secret123"})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert r.status_code == 200 and r.json()["full_name"] == "Test Patient"
    return r.json()["user_id"]


def check_in(client, user_id, pairs):
    for score, mobility in pairs:
        r = client.post("/pain/submit", params={"score": score, "mobility": mobility, "notes": "", "user_id": user_id})
        assert r.status_code == 200


def recommend(client, user_id, age=AGE, exercise=EXERCISE, guidance=True):
    r = client.post("/engine/recommend", json={"user_id": user_id, "age": age, "exercise_frequency": exercise,
                                               "include_guidance": guidance})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_patient_journey(client):
    # 1. Account
    uid = register_and_login(client, "patient@example.com")

    # 2. Injury report
    r = client.post("/injury/submit", params={"injury_type": "knee", "symptoms": "stiffness", "pain_level": 7,
                                              "user_id": uid})
    assert r.status_code == 200
    assert client.get(f"/injury/user/{uid}").json()[0]["injury_type"] == "knee"

    # 3. Too few check-ins: the plan holds at beginner
    check_in(client, uid, [(7, 4), (7, 4)])
    r = recommend(client, uid, guidance=False)
    assert r["decision"] == "hold" and r["level_after"] == "beginner"

    # 4. Pain going down, mobility going up: moves up to intermediate, with exercises for that level
    check_in(client, uid, [(6, 5), (5, 6), (4, 7), (3, 7)])
    r = recommend(client, uid)
    assert r["pain_trend"] == "decreasing" and r["mobility_trend"] == "increasing"
    assert r["decision"] == "progress" and r["level_after"] == "intermediate"
    assert r["exercise_guidance"]["level"] == "intermediate"
    assert "Start with these exercises" in r["exercise_guidance"]["guidance"]
    assert r["anomaly_check"]["is_anomaly"] is False
    assert r["recovery_timeline"]["predicted_recovery_weeks"] > 0
    assert client.get(f"/engine/state/{uid}").json()["level"] == "intermediate"

    # 5. Asking again right away doesn't jump another level (needs 3 new check-ins first)
    r = recommend(client, uid, guidance=False)
    assert r["level_after"] == "intermediate"

    # 6. Pain going back up: back to beginner, and the user is told why
    check_in(client, uid, [(5, 6), (6, 5), (7, 4)])
    r = recommend(client, uid, guidance=False)
    assert r["decision"] == "regress" and r["level_after"] == "beginner"
    notes = client.get(f"/engine/notifications/{uid}").json()
    assert [n["decision"] for n in notes][:2] == ["regress", "progress"]

    # 7. Progress screen data
    assert len(client.get(f"/pain/history/{uid}").json()) == 9
    body = {"age": AGE, "pain_severity": "Severe", "exercise_frequency": EXERCISE}
    assert client.post("/recovery-model/predict", json=body).json()["predicted_recovery_weeks"] > 0
    assert client.post("/autoencoder/check", json=body).json()["is_anomaly"] is False

    # 8. Insurance: file a claim, log a check-in after it, open the report
    claim_id = client.post("/insurance/submit-claim", params={"user_id": uid, "injury_type": "knee",
                                                              "expected_recovery_weeks": 8}).json()["claim_id"]
    check_in(client, uid, [(5, 6)])
    r = client.get(f"/insurance/claims/{claim_id}/report", params={"age": AGE, "exercise_frequency": EXERCISE})
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["risk"]["risk_level"] in ("low", "medium", "high")
    assert report["insights"][0].startswith("Patients like you recover in about")
    assert report["predictive_timeline"]["model_predicted_weeks"] > 0
    for chart in report["charts"].values():
        png = client.get(chart)
        assert png.status_code == 200 and png.headers["content-type"] == "image/png"

    # 9. The app page is served
    page = client.get("/app/")
    assert page.status_code == 200 and "PT IntelliCare" in page.text


def test_unusual_profile_pauses_progress(client):
    """Anomaly detected -> progression paused and the user is notified, even though pain is improving."""
    uid = register_and_login(client, "unusual@example.com")
    client.post("/injury/submit", params={"injury_type": "hip", "symptoms": "ache", "pain_level": 3, "user_id": uid})
    check_in(client, uid, [(4, 5), (4, 5), (3, 6), (2, 7), (1, 8), (1, 8)])   # improving, latest pain 1
    r = recommend(client, uid, age=60, exercise="I always exercise.", guidance=False)
    assert r["anomaly_check"]["is_anomaly"] is True
    assert r["decision"] == "pause" and r["level_after"] == "beginner"
    assert r["notification"] and "paused" in r["notification"]


def test_high_pain_goes_to_beginner(client):
    uid = register_and_login(client, "highpain@example.com")
    client.post("/injury/submit", params={"injury_type": "back", "symptoms": "sharp pain", "pain_level": 9,
                                          "user_id": uid})
    check_in(client, uid, [(8, 3), (9, 2), (9, 2), (9, 2)])
    r = recommend(client, uid, age=25, exercise="I exercise sometimes.", guidance=False)
    assert r["level_after"] == "beginner"
    assert "high" in r["reasons"][0] or r["decision"] == "pause"


def test_missing_injury_gives_a_clear_error(client):
    uid = register_and_login(client, "noinjury@example.com")
    r = client.post("/engine/recommend", json={"user_id": uid, "age": 30, "exercise_frequency": EXERCISE,
                                               "include_guidance": False})
    assert r.status_code == 404 and "injury" in r.json()["detail"].lower()
