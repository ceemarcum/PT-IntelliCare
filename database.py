import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Locally: capstone.db. On Cloud Run: whatever DATABASE_URL is set to (e.g. Cloud SQL Postgres).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./capstone.db")

# check_same_thread is a SQLite-only setting
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()