# Step 8: Testing & Validation

**Result: 77 automated tests, all passing.** Run them from the Capstone_Backend folder:

```
py -m pip install -r requirements-test.txt
py -m pytest -v
```

The tests use a temporary database (capstone.db is never touched) and a fake RAG answer (no OpenAI calls or cost).

| Test file | Tests | What it covers |
|---|---|---|
| `test_recovery_model.py` | 29 | Linear Regression recovery predictions |
| `test_autoencoder.py` | 12 | Anomaly detection |
| `test_rag_guidance.py` | 12 | RAG search, question, prompt and safety warning |
| `test_engine_rules.py` | 9 | Exercise level rules |
| `test_insurance_analytics.py` | 7 | Insurance calculations |
| `test_insurance_validation.py` | 4 | Insurance reports on two known patients |
| `test_end_to_end.py` | 4 | The full app flow through the API |

## 1. Each model tested separately

### Recovery time model (Linear Regression)

Model results from `linear_regression/recovery_lr.ipynb` (same data and split for both models):

| | Linear Regression | Random forest |
|---|---|---|
| Test set R² | 0.463 | 0.422 |
| Test set RMSE | 1.615 weeks | 1.675 weeks |
| 5-fold cross-validation R² | **0.499** | 0.448 |
| 5-fold cross-validation RMSE | **1.479 weeks** | 1.552 weeks |

Linear Regression won on every cross-validation fold, so the app uses it. The simulation adds random noise of about 1.5 weeks, so an RMSE of 1.48 is close to the best any model could do on this data.

### Autoencoder (anomaly detection)

Trained in TensorFlow/Keras in `autoencoder/preprocess.ipynb`. The threshold is 0.163, the 95th percentile of training reconstruction errors. The app runs the same weights with NumPy because Windows Smart App Control blocks TensorFlow's DLLs. The NumPy version matches the Keras model's reconstruction errors to within 0.001 on 5 reference profiles (checked to within 0.0000001 on 500 random profiles when it was switched).

### RAG (exercise guidance)

Tested with a fake vector store and fake LLM:

- it searches for "[injury] exercises" rather than the patient's whole sentence, and retrieves 6 chunks
- the question includes the injury, pain level, symptoms and exercise level
- the prompt requires named exercises from the sources, in a numbered list, plus movements to avoid
- the prompt includes the safety rule (pain 8/10 or higher, numbness or tingling: see a professional)
- the code itself adds the safety warning in those cases, so it can't be skipped (see below)
- sources show the PDF name and page, or the web link

## 2. Full pipeline, end to end

`test_end_to_end.py` runs a patient through the real API:

1. Register and log in.
2. Report a knee injury (pain 7).
3. 2 check-ins: the plan **holds** at beginner (not enough data).
4. 4 more check-ins with pain falling and mobility rising: **moves up** to intermediate, with exercises for that level.
5. Asking again right away: **stays** at intermediate (needs 3 new check-ins first).
6. Pain rising again: **back to beginner**, with a notification explaining why.
7. Progress data: check-in history, recovery prediction, anomaly check.
8. File an insurance claim, log a check-in, open the report: risk, insights, timeline, and both charts load as images.
9. The PT IntelliCare app page loads.

Extra end-to-end cases: an unusual profile **pauses** progress, high pain (8 or more) keeps the plan at **beginner**, and a missing injury gives a **clear error**.

## 3. Validation

### Exercise recommendations make sense

| Situation | Expected | Result |
|---|---|---|
| Fewer than 4 check-ins | Hold | Pass |
| Pain decreasing, mobility improving | Move up one level | Pass |
| Moved up, no new check-ins | Don't jump again | Pass |
| Pain increasing | Back to beginner | Pass |
| Pain 8/10 or higher | Beginner | Pass |
| Autoencoder flags the profile | Pause and notify | Pass |
| Pain 8+, numbness, tingling or can't bear weight | "See a doctor or physical therapist" warning on the exercises | Pass |
| Exercises returned | Match the new level | Pass |

**Manual check of the real RAG answers** (needs the OpenAI key; fill in after running `POST /rag/guidance` or **Update my plan** in the app):

| Injury, pain, level | Named exercises with amounts? | Fit the level? | Notes |
|---|---|---|---|
| Neck, 8/10, numbness (no level) | Yes: chin tucks, neck stretches, shoulder rolls | | The AI left out the "see a doctor" advice, so the backend now adds it itself |
| Knee, 6/10, intermediate | | | |
| Neck, 2/10, intermediate | | | |
| Lower back, 8/10, beginner | | | |

### Recovery predictions are reasonable

Age 30, "I exercise sometimes":

| Pain | Not severe at all | Mild | Moderate | Severe | Very severe |
|---|---|---|---|---|---|
| Predicted weeks | 4.6 | 5.9 | 7.1 | 8.3 | 9.5 |

Age 30, moderate pain:

| Exercise | Not at all | Sometimes | Most of the time | Always |
|---|---|---|---|---|
| Predicted weeks | 7.9 | 7.1 | 6.2 | 5.4 |

- More pain, older age and less exercise all mean longer recovery, as expected.
- Every prediction stays between 2 and 30 weeks, inside its own likely range.
- The likely range contains **80.6%** of the historical patients' real recovery times (target: 80%).
- For ages 18 to 30, predictions are within 2 weeks of the median for similar historical patients.

**Limitation:** most survey respondents were 18 to 30, so predictions for older patients are an extrapolation of the same trend.

### Anomaly detection triggers correctly

| Profile | Error | Result |
|---|---|---|
| 22, Moderate, exercises sometimes | 0.003 | Typical |
| 30, Mild, exercises sometimes | 0.004 | Typical |
| 24, Severe, never exercises | 0.117 | Typical |
| 70, Very severe, always exercises | 0.304 | **Unusual** |
| 60, Not severe at all, always exercises | 0.271 | **Unusual** |

Threshold: 0.163. On the full survey, **5 of 95 people (5.3%)** are flagged, which matches the 95th-percentile threshold (about 5% expected).

### Insurance analytics are accurate

Two known patients with 6 weeks of history:

| | On-track patient | Slow patient |
|---|---|---|
| Pain | 7 down to 1 | Stays 6 to 7 |
| Check-ins per week | 3, 3, 3, 3, 3, 3 | 2, 1, 1, 1, 1, 1 |
| Engagement | 100% | 39% (1.2 a week vs a target of 3) |
| Status | Faster than expected | Slower than expected |
| Risk | **Low** (0 points) | **High** (4 points: past the 5-week estimate with pain 7, behind the expected curve, low engagement) |
| Flagged for early intervention | No | Yes |

- The "patients like you" numbers (count, median, 25th and 75th percentile) match a direct calculation on `historical_recovery.csv`.
- The flagged list contains only the slow patient, and the portfolio counts 1 low and 1 high.
- Opening a report updates the claim's `flagged` field in the database.

## Notes

- **PT utilization** uses app check-ins as a stand-in for therapy sessions, since there's no attendance data yet.
- **Simulated data:** recovery times are simulated from the Pain Data survey (see `random_forest/recovery_rf.ipynb`). With real patient data the models would be retrained and these tests re-run.
