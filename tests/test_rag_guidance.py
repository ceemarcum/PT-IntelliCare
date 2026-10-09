"""
RAG exercise guidance (rag/guidance.py), with a fake vector store and fake LLM so no OpenAI calls are made.
Checks the question, search and prompt the RAG builds. Whether the real answers make sense is checked
by hand (see VALIDATION.md).
"""
import pytest

# Skipped (not failed) if LangChain or Chroma can't load on this computer
g = pytest.importorskip("rag.guidance")


class Doc:
    def __init__(self, text, source, page=0):
        self.page_content = text
        self.metadata = {"source": source, "page": page}


class FakeStore:
    def __init__(self):
        self.query, self.k = None, None

    def similarity_search(self, query, k):
        self.query, self.k = query, k
        return [Doc("Chin tucks: hold 5 seconds, 10 times.", "C:/data/pdfs/guide.pdf", 2),
                Doc("Neck rotations: 10 each side.", "C:/data/pdfs/guide.pdf", 2),      # same page: listed once
                Doc("Neck pain overview.", "https://medlineplus.gov/neckinjuriesanddisorders.html")]


class FakeLLM:
    def __init__(self):
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return type("Msg", (), {"content": "**Start with these exercises**\n1. **Chin tucks**: hold 5 seconds."})()


@pytest.fixture
def fakes(monkeypatch):
    store, llm = FakeStore(), FakeLLM()
    monkeypatch.setattr(g, "vectorstore", store)
    monkeypatch.setattr(g, "llm", llm)
    return store, llm


def test_searches_for_exercises_not_the_whole_sentence(fakes):
    store, _ = fakes
    g.exercise_guidance("neck", 2, "stiffness", level="intermediate")
    assert store.query.startswith("neck exercises")
    assert store.k == 6


def test_question_includes_injury_pain_symptoms_and_level(fakes):
    _, llm = fakes
    g.exercise_guidance("neck", 2, "stiffness, dull ache", level="intermediate")
    assert "neck injury" in llm.prompt and "2/10" in llm.prompt
    assert "stiffness, dull ache" in llm.prompt
    assert "recommend intermediate exercises" in llm.prompt


def test_prompt_asks_for_named_exercises_in_a_list(fakes):
    _, llm = fakes
    g.exercise_guidance("knee", 6, "swelling", level="beginner")
    assert "**Start with these exercises**" in llm.prompt
    assert "**Avoid these movements for now**" in llm.prompt
    assert "specific, named exercise" in llm.prompt
    assert "Do not invent exercises" in llm.prompt


def test_prompt_includes_the_safety_rule(fakes):
    _, llm = fakes
    g.exercise_guidance("knee", 9, "numbness")
    assert "8/10 or higher" in llm.prompt and "numbness" in llm.prompt


def test_context_and_sources(fakes):
    _, llm = fakes
    r = g.exercise_guidance("neck", 4)
    assert "Chin tucks: hold 5 seconds" in llm.prompt                  # retrieved text is given to the LLM
    assert r["sources"] == ["guide.pdf, page 3",                        # PDFs: file name + page (1-based)
                            "https://medlineplus.gov/neckinjuriesanddisorders.html"]
    assert r["guidance"].startswith("**Start with these exercises**")


@pytest.mark.parametrize("pain,symptoms", [(8, "strained"), (5, "numbness, strained"), (3, "tingling in fingers"),
                                            (6, "can't bear weight")])
def test_safety_warning_is_always_added(fakes, pain, symptoms):
    """The AI skipped this advice once (neck, pain 8, numbness), so the code adds it itself."""
    r = g.exercise_guidance("neck", pain, symptoms)
    assert r["safety_warning"] and "see a doctor or physical therapist" in r["safety_warning"]
    assert r["guidance"].endswith(r["safety_warning"])


@pytest.mark.parametrize("pain,symptoms", [(7, "stiffness"), (2, "dull ache"), (5, "")])
def test_no_safety_warning_when_not_needed(fakes, pain, symptoms):
    r = g.exercise_guidance("knee", pain, symptoms)
    assert r["safety_warning"] is None and "see a doctor" not in r["guidance"]

