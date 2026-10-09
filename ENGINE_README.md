# Step 5: Dynamic Exercise Recommendation Engine

`POST /engine/recommend` combines the user's saved check-ins with all three models and sets their exercise level.

| Input | Where it comes from |
|---|---|
| Pain and mobility trends | The user's check-ins (`POST /pain/submit` with `user_id`) |
| Anomaly alert | Autoencoder (`routes/autoencoder_routes.py`) |
| Predicted recovery time | Linear Regression (`routes/recovery_routes.py`) |
| Exercises for the chosen level | RAG (`rag/guidance.py`) |

## Rules (in `engine/rules.py`, checked in this order)

1. **Anomaly detected:** pause progression (keep the level) and notify the user.
2. **Latest pain 8/10 or higher:** back to beginner and notify.
3. **Pain increasing:** revert to beginner and notify.
4. **Fewer than 4 check-ins:** hold until there's enough to see a trend.
5. **Pain decreasing (mobility not worse), or pain steady and low (4/10 or less) with mobility improving:** progress one level (beginner → intermediate → advanced) and notify. Moving up again needs 3 new check-ins at the current level.
6. **Otherwise:** hold at the current level.

**Trend:** the average of the last 3 check-ins compared with the 3 before them. A change of 1 point or more counts as going up or down.

## Endpoints

| Endpoint | What it does |
|---|---|
| `POST /engine/recommend` | Runs the engine for a user and saves their new level |
| `GET /engine/state/{user_id}` | The user's current level |
| `GET /engine/notifications/{user_id}` | Plan changes and pauses, newest first |
| `GET /pain/history/{user_id}` | The user's check-ins |

`POST /pain/submit` and `POST /injury/submit` now take an optional `user_id`, so check-ins and injuries belong to a user.

## Test it

1. Register a user (`POST /auth/register`). The response now includes their `user_id` (login returns it too). The steps below use 1; use yours.
2. `POST /injury/submit`: `injury_type` knee, `symptoms` stiffness, `pain_level` 7, `user_id` 1.
3. `POST /pain/submit` six times with `user_id` 1 (score / mobility): 7/4, 7/4, 6/5, 5/6, 4/7, 3/7.
4. `POST /engine/recommend` with:
   ```
   {"user_id": 1, "age": 30, "exercise_frequency": "I exercise sometimes.", "include_guidance": true}
   ```
   Expected: `"decision": "progress"`, beginner → intermediate, plus RAG exercises for intermediate.
5. Add three higher check-ins (5/6, 6/5, 7/4) and run step 4 again. Expected: `"decision": "regress"`, back to beginner.

Set `"include_guidance": false` to skip the RAG call (faster, no OpenAI cost).

Unit tests for the rules: `py -m pytest tests`
