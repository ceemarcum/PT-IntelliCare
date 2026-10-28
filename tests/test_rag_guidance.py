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

    def get(self, include=None):
        return {"metadatas": [{"source": "C:\\data\\pdfs\\wwl-low-back-level-1.pdf"}]}

    def similarity_search(self, query, k, filter=None):
        if filter:                                     # search inside one handout
            self.filter = filter
            return [Doc("Pelvic tilts (sitting): 10 times.", filter["source"])]
        self.query, self.k = query, k
        return [Doc("Wrong level: front plank.", "C:\\data\\pdfs\\wwl-low-back-level-3.pdf"),
                Doc("Chin tucks: hold 5 seconds, 10 times.", "C:/data/pdfs/guide.pdf", 2),
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
    monkeypatch.setattr(g, "_sources", None)
    return store, llm


def test_searches_for_exercises_not_the_whole_sentence(fakes):
    store, _ = fakes
    g.exercise_guidance("neck", 2, "stiffness", level="intermediate")
    assert store.query.startswith("neck exercises")
    assert store.k == g.K * 2          # extra chunks, so other handouts can be left out


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
    assert "Use exercises from the context" in llm.prompt
    assert "(general suggestion, not from the sources)" in llm.prompt


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


@pytest.mark.parametrize("injury,level,handout", [
    ("lower back", "beginner", "wwl-low-back-level-1.pdf"), ("back", "advanced", "wwl-low-back-level-3.pdf"),
    ("neck", "intermediate", "wwl-neck-level-2.pdf"), ("knee", "beginner", "aaos-knee-conditioning.pdf"),
    ("shoulder", None, "aaos-shoulder-conditioning.pdf"), ("ankle", "beginner", None)])
def test_handout_matches_injury_and_level(injury, level, handout):
    assert g.handout_for(injury, level) == handout


def test_matching_handout_is_always_searched_and_other_handouts_dropped(fakes):
    store, llm = fakes
    r = g.exercise_guidance("lower back", 5, level="beginner")
    assert store.filter == {"source": "C:\\data\\pdfs\\wwl-low-back-level-1.pdf"}
    assert "Pelvic tilts (sitting)" in llm.prompt                 # from the Level 1 leaflet
    assert "Wrong level" not in llm.prompt                         # Level 3 chunk left out
    assert r["sources"][0].startswith("Exercise leaflets from Wrightington")
