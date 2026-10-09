# PT IntelliCare

A physical therapy recovery app that adapts a patient's exercise plan as they heal, and gives insurers early warning on claims that are off track.

Patients log an injury and daily pain and mobility check-ins. Three ML components (a recovery time model, an anomaly detector and a RAG exercise guide) feed a rules engine that moves the patient between beginner, intermediate and advanced exercises. An insurance module compares each claim's recovery with similar historical patients and flags the ones that need early intervention.

**Live demo:** https://pt-intellicare-950512703431.us-central1.run.app/app

| Demo account | Password | Story |
|---|---|---|
| `demo.ontrack@example.com` | `demo1234` | Knee injury, pain dropping steadily, frequent check-ins |
| `demo.slow@example.com` | `demo1234` | Lower back injury, pain barely improving, rare check-ins |

The first sign-in on a browser asks for age and exercise habits (try 30 and "I exercise sometimes."). The first visit after a quiet period takes a few seconds while the server wakes up.

> Built as a capstone project with simulated recovery data. Not medical advice.

## Features

- **Injury intake and daily check-ins** with 0 to 10 pain and mobility sliders
- **Adaptive exercise plan** that progresses, holds or steps back based on pain trends and anomaly alerts
- **Personalized exercise guidance** from physical therapy sources (RAG), with sources cited and a safety warning for severe pain, numbness or tingling
- **Recovery time prediction** with a likely range
- **Progress dashboard** charting pain and mobility over time
- **Insurance insights:** recovery tracking, comparison with similar patients, risk score and early intervention flags
- **Monitoring:** error rates, user engagement and model performance, with uptime and error alerts

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite, JWT auth (python-jose, passlib/bcrypt) |
| Machine learning | scikit-learn (Linear Regression), TensorFlow/Keras autoencoder served with NumPy, pandas |
| RAG | LangChain, OpenAI embeddings and gpt-4o-mini, Chroma vector store |
| Frontend | React, Vite, React Router, custom SVG charts |
| Testing | pytest (77 tests) |
| Deployment | Docker, Google Cloud Run, Cloud Build, Artifact Registry, Secret Manager |
| Monitoring | Cloud Run metrics, Cloud Logging (structured JSON logs), Cloud Monitoring uptime check and alerts |

## How it works

```
Patient (React app at /app)
        |
        v
FastAPI backend ------------------------------> SQLite (users, injuries, check-ins, claims)
   |-- Recovery model (Linear Regression)     -> predicted recovery weeks
   |-- Autoencoder (anomaly detection)        -> flags unusual pain profiles
   |-- RAG (LangChain + Chroma + OpenAI)      -> exercises for the patient's level
   |-- Recommendation engine (rules)          -> progress / hold / step back
   |-- Insurance analytics                    -> risk score, early intervention flags
   '-- Monitoring                             -> /monitoring/summary + JSON logs
```

## Models

| Model | What it does | Result |
|---|---|---|
| **Linear Regression** (`linear_regression/`) | Predicts recovery time in weeks from age, pain severity and exercise level | 5-fold CV RMSE 1.48 weeks, R² 0.50. Beat a random forest (RMSE 1.55), which is kept in `random_forest/` for comparison |
| **Autoencoder** (`autoencoder/`) | Flags pain profiles that don't look like the training data | Threshold at the 95th percentile of training reconstruction error. Trained in Keras, served with NumPy (matches Keras within 0.001) |
| **RAG** (`rag/`) | Answers "which exercises should I do?" from PT sources | Retrieves 6 chunks with an exercise-focused search, cites PDF pages and web links, and always adds the safety warning in code |

The recommendation engine (`engine/rules.py`) combines them. Anomalies pause progression, pain of 8/10 or more or rising pain steps back to beginner, and falling pain with enough check-ins moves up a level. See [ENGINE_README.md](ENGINE_README.md).

## Monitoring

| What | Where |
|---|---|
| Error rates, latency, user engagement, model performance (prediction drift vs training data, anomaly rate vs the expected 5%, RAG speed and failures, engine decisions) | `GET /monitoring/summary` |
| Health check | `GET /monitoring/health` |
| Every prediction, anomaly check, RAG call, engine decision and server error as a searchable JSON log | Cloud Logging, filter `jsonPayload.event` |
| Email alerts when the app is down or returns more than 2 server errors in 5 minutes | Cloud Monitoring |

## Run it locally

Requires Python 3.12 and an OpenAI API key (for the RAG guidance only).

```
py -m pip install -r requirements.txt
copy .env.example .env
```

Put your key in `.env` after `OPENAI_API_KEY=`, then start the server:

```
py -m uvicorn main:app --reload
```

- App: http://127.0.0.1:8000/app
- API docs: http://127.0.0.1:8000/docs
- Load the demo patients: `py -m insurance.demo_seed`

The RAG vector store (`chroma_db/`) is included. The source PDFs are not, so rebuilding it with `py -m rag.build_index` needs them added to `data/pdfs/` first (see [RAG_README.md](RAG_README.md)).

To change the React code, see [FRONTEND_README.md](FRONTEND_README.md).

## Tests

```
py -m pip install -r requirements-test.txt
py -m pytest -v
```

77 tests cover each model, the RAG prompt and safety warning, the engine rules, the insurance calculations and a full patient journey through the API. They use a temporary database and a fake RAG answer, so they make no OpenAI calls. Results are in [VALIDATION.md](VALIDATION.md).

## Deploy to Google Cloud Run

The `Dockerfile` builds the whole app (backend, models and the built React app) into one container. From the project folder:

```
gcloud run deploy pt-intellicare --source . --region us-central1 \
  --service-account pt-intellicare-run@pt-intellicare.iam.gserviceaccount.com \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-env-vars SEED_DEMO=1 --memory 1Gi --max-instances 1 --allow-unauthenticated
```

- The OpenAI key comes from Secret Manager, never from the code.
- `SEED_DEMO=1` loads the demo patients at startup.
- SQLite lives inside the container, so data resets when the app restarts. `--max-instances 1` keeps everyone on the same database. A production version would use a managed database such as Cloud SQL.

## Project structure

```
main.py                 FastAPI app: routes, monitoring middleware, serves the React app
routes/                 API endpoints (auth, injury, pain, recovery model, autoencoder, RAG, engine, insurance, monitoring)
models/  schemas/       Database tables and request/response shapes
linear_regression/      Recovery time model (notebook + trained model)
autoencoder/            Anomaly detector (notebook, weights, NumPy export)
random_forest/          Earlier recovery model, kept for comparison
rag/                    Vector store builder and guidance logic
engine/                 Exercise level rules
insurance/              Claim analytics, charts and demo data
monitoring/             Request and model metrics, JSON logging
frontend-react/         React app (src) and its production build (dist)
tests/                  pytest suite
data/                   Survey data and simulated recovery history
```

## Data

- `data/Pain Data.xlsx`: survey responses on pain severity and exercise habits
- `data/historical_recovery.csv`: simulated patient recovery times shaped by the survey, used to train the recovery model and as the insurance comparison group
- RAG sources: physical therapy PDFs plus MedlinePlus and NIAMS web pages
