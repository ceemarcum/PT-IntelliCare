import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Routers
from routes.auth_routes import router as auth_router
from routes.injury_routes import router as injury_router
from routes.pain_routes import router as pain_router
from routes.recommendation_routes import router as recommendation_router
from routes.insurance_routes import router as insurance_router
from routes.rag_routes import router as rag_router
from routes.autoencoder_routes import router as autoencoder_router
from routes.recovery_routes import router as recovery_router
from routes.engine_routes import router as engine_router
from routes.monitoring_routes import router as monitoring_router
from monitoring.metrics import track_requests

# Database
from database import Base, engine

app = FastAPI()

app.middleware("http")(track_requests)

@app.get("/")
def home():
    return {"message": "Backend is running!"}

# Include routers
app.include_router(auth_router)
app.include_router(injury_router)
app.include_router(pain_router)
app.include_router(recommendation_router)
app.include_router(insurance_router)
app.include_router(rag_router)
app.include_router(autoencoder_router)
app.include_router(recovery_router)
app.include_router(engine_router)
app.include_router(monitoring_router)

# Create database tables
Base.metadata.create_all(bind=engine)

# Cloud Run: the SQLite database starts empty on every restart, so load the demo patients (only when SEED_DEMO=1)
if os.getenv("SEED_DEMO") == "1":
    from insurance.demo_seed import seed
    seed()

# Frontend (Step 7): the React app, built into frontend-react/dist. It's at http://127.0.0.1:8000/app
app.mount("/app", StaticFiles(directory=Path(__file__).resolve().parent / "frontend-react" / "dist", html=True), name="frontend")
