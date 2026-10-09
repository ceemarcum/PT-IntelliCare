"""
Shared test setup (Step 8: Testing & Validation).

- Every API test uses its own empty database in a temp folder, so capstone.db is never touched.
- The RAG is replaced with a fake answer, so tests never call OpenAI (no cost, no API key needed).

Run from the Capstone_Backend folder:  py -m pytest tests -v
"""
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAKE_GUIDANCE = ("**Start with these exercises**\n"
                 "1. **Heel slides**: 2 sets of 10. Slide your heel toward you and back.\n"
                 "2. **Quad sets**: hold 5 seconds, 10 times. Tighten the front of your thigh.\n\n"
                 "**Avoid these movements for now**\n- Deep squats\n- Running")


def fake_guidance(injury, pain_level, symptoms="", level=None):
    return {"injury_type": injury, "pain_level": pain_level, "symptoms": symptoms, "level": level,
            "guidance": FAKE_GUIDANCE, "sources": ["fake-guide.pdf, page 1"]}


@pytest.fixture
def session_factory(tmp_path):
    """A fresh, empty database for one test."""
    import main  # noqa: F401  (registers every table)
    from database import Base
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autocommit=False, autoflush=False)
    engine.dispose()


@pytest.fixture
def client(session_factory, monkeypatch):
    """The real FastAPI app, pointed at the test database, with the fake RAG."""
    from fastapi.testclient import TestClient
    import main
    from database_session import get_db

    def test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = test_db
    # Swap in a fake rag.guidance module, so the real one (LangChain, Chroma, OpenAI) isn't even imported
    fake_rag = types.ModuleType("rag.guidance")
    fake_rag.exercise_guidance = fake_guidance
    monkeypatch.setitem(sys.modules, "rag.guidance", fake_rag)
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
