# Step 6: Insurance Analytics Module

Tracks each claim's recovery after it's filed, compares it with similar historical patients, and flags cases that need early intervention.

| Feature | Where it comes from |
|---|---|
| Recovery tracking | The user's check-ins after the claim date (`POST /pain/submit` with `user_id`), averaged per week |
| Historical averages | `data/historical_recovery.csv` (from recovery_rf.ipynb): patients with a similar age, starting pain and exercise level |
| Predictive timeline | Linear Regression estimate, the insurer's expected weeks, and a projection from the user's own pain trend |
| Risk and early intervention | Points system below, plus the autoencoder anomaly check |
| PT utilization | Check-ins per week vs a target of 3. This stands in for therapy attendance until real PT session data exists |

Code: `insurance/analytics.py` (calculations), `insurance/charts.py` (graphs), `models/claim_analysis_model.py` (saved results), `routes/insurance_routes.py` (endpoints).

## Risk points

| Risk factor | Points |
|---|---|
| Autoencoder flags the pain profile as unusual | 2 |
| Past the insurer's expected weeks and pain still above 3/10 | 2 |
| Pain increasing over recent check-ins | 1 |
| The recovery model predicts slower than most similar patients (above their 75th percentile) | 1 |
| Pain more than 1.5 points above the expected curve | 1 |
| Fewer than half the target check-ins | 1 |

0-1 is **low**, 2-3 **medium**, 4 or more **high**. A claim is flagged for early intervention if it's high risk, the autoencoder flags it, or it's past the expected weeks with pain still above 3/10. The report sets the claim's `flagged` field.

**Expected curve:** pain falls smoothly from the starting pain to 2/10 (recovered) by the similar patients' median recovery time. The shaded band covers their 25th to 75th percentile.

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /insurance/claims/{claim_id}/report?age=&exercise_frequency=` | Full report: insights, risk, tracking, comparison, timeline, utilization. Saves the result |
| `GET /insurance/claims/{claim_id}/chart/recovery-trend.png` | Graph: weekly pain vs the expected curve |
| `GET /insurance/claims/{claim_id}/chart/utilization.png` | Graph: check-ins per week vs the target |
| `GET /insurance/portfolio` | All analyzed claims: risk counts, patterns by injury type and risk level |
| `GET /insurance/portfolio/chart/risk.png` | Graph: claims by risk level |
| `GET /insurance/flagged` | Claims needing early intervention, highest risk first |

The chart endpoints reuse the age and exercise answer saved by the last report, so run the report first. The original `POST /insurance/submit-claim` and `GET /insurance/analytics/{user_id}` are unchanged.

## Test it

1. `py -m pip install -r requirements-insurance.txt`
2. Load demo data (two patients whose claims were filed 6 weeks ago): `py -m insurance.demo_seed`. It prints each patient's `claim_id`.
3. Start the server and open http://127.0.0.1:8000/docs.
4. Run the report for each claim with `age` 30 and `exercise_frequency` "I exercise sometimes.":
   - On-track patient: low risk, "trending faster than expected", not flagged.
   - Slow patient: high risk, "trending slower than expected", flagged.
5. Open the chart links in the browser, e.g. http://127.0.0.1:8000/insurance/claims/1/chart/recovery-trend.png (use your claim_id).
6. `GET /insurance/portfolio` and `GET /insurance/flagged`.

Unit tests: `py -m pytest tests`
