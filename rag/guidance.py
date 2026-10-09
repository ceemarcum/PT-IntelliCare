"""
Step 2 of the RAG: answer questions (used by the API on every request).

This is the notebook's retrieve and prompt cells. It opens the vector store saved by
build_index.py instead of rebuilding it.
"""
import os
import time

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from monitoring.metrics import record_rag

from rag.config import CHROMA_DIR, EMBEDDING_MODEL, CHAT_MODEL, check_api_key

PROMPT_TEMPLATE = """
You are a supportive physical therapy assistant. Address the patient directly and briefly acknowledge their pain level and symptoms in one sentence.

Exercise levels (the guides don't label levels, so use these definitions):
- beginner: gentle range-of-motion, stretching and isometric (no movement) exercises
- intermediate: the beginner exercises plus light strengthening (bodyweight or resistance bands)
- advanced: progressive strengthening, balance and functional or sport-like exercises
If the question names a level, use it. Otherwise pick from the pain level: 7-10 beginner, 4-6 intermediate, 0-3 advanced.

Answer in exactly this format:

**Start with these exercises**
1. **Exercise name**: sets and reps or hold time. One sentence on how to do it.
(list 3 to 5 exercises)

**Avoid these movements for now**
- one movement per line (2 to 4 lines)

Rules:
- Every exercise must be a specific, named exercise found in the context below (for example "chin tucks", not "gentle neck stretches"). Do not invent exercises.
- Use the sets, reps or hold times from the context. If the context gives none for an exercise, write "amount: as advised by your physical therapist" instead of making numbers up.
- If the context has no exercises for this body part, say so in one sentence instead of giving general advice.
- Do not diagnose. If pain is 8/10 or higher, or there is numbness, tingling or inability to bear weight, add a final line advising them to see a doctor or physical therapist before exercising.

Context:
{context}

Question:
{question}

Answer:
"""

K = 6   # chunks retrieved per question

# Safety: added by the code itself, so it never depends on the AI remembering the rule
HIGH_PAIN = 8
RED_FLAGS = ["numb", "tingl", "pins and needles", "can't bear weight", "cannot bear weight", "unable to bear weight",
             "can't walk", "cannot walk", "weakness in", "loss of bladder", "loss of bowel"]
SAFETY_MESSAGE = ("**Please check with a professional first:** with {reason}, see a doctor or physical therapist "
                  "before starting these exercises. Stop any exercise that makes your symptoms worse.")


def safety_warning(pain_level, symptoms=""):
    """Returns the safety message if pain is 8/10 or higher or a red-flag symptom is listed, else None."""
    reasons = []
    if pain_level >= HIGH_PAIN:
        reasons.append(f"pain at {pain_level}/10")
    flags = [f for f in RED_FLAGS if f in (symptoms or "").lower()]
    if flags:
        reasons.append("numbness or tingling" if any(f in ("numb", "tingl", "pins and needles") for f in flags)
                       else "these symptoms")
    return SAFETY_MESSAGE.format(reason=" and ".join(reasons)) if reasons else None


vectorstore = None
llm = None


def load():
    """Open the saved vector store and the LLM once, on the first question."""
    global vectorstore, llm
    if vectorstore is None:
        check_api_key()
        if not CHROMA_DIR.exists():
            raise RuntimeError("The vector store isn't built yet. Run: py -m rag.build_index")
        vectorstore = Chroma(persist_directory=str(CHROMA_DIR),
                             embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL))
        llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)


def rag_query(question, search_query=None):
    """search_query: what to look up in the vector store (defaults to the question itself)."""
    load()
    chunks = vectorstore.similarity_search(search_query or question, k=K)
    context = "\n\n---\n\n".join([c.page_content for c in chunks])
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    response = llm.invoke(prompt)
    # web pages keep their link; PDFs show the file name and page
    sources = []
    for c in chunks:
        src = c.metadata.get("source", "")
        if not src.startswith("http"):
            src = f"{os.path.basename(src)}, page {c.metadata.get('page', 0) + 1}"
        if src not in sources:
            sources.append(src)
    return response.content, sources


def exercise_guidance(injury, pain_level, symptoms="", level=None):
    """level: the exercise level chosen by the recommendation engine (beginner, intermediate, advanced)."""
    question = (f"I have a {injury} injury. My pain level is {pain_level}/10. "
                f"Symptoms: {symptoms or 'none listed'}. Which exercises should I start with, "
                f"and which movements should I avoid for now?")
    if level:
        question += f" My exercise level is {level}, so recommend {level} exercises."
    # Search with an exercise-focused query so the chunks that list exercises come back,
    # rather than general text about pain that matches the patient's sentence
    search_query = (f"{injury} exercises: stretching, range of motion and strengthening exercises "
                    f"for {injury} pain, with sets, repetitions and hold times")
    
    start = time.perf_counter()
    try:
        answer, sources = rag_query(question, search_query)
    except Exception as exc:                      # record the failure for monitoring, then pass it on
        record_rag(False, round(time.perf_counter() - start, 2), error=repr(exc))
        raise
    warning = safety_warning(pain_level, symptoms)
    if warning:
        answer = f"{answer.rstrip()}\n\n{warning}"
    record_rag(True, round(time.perf_counter() - start, 2), warning)
    return {"injury_type": injury, "pain_level": pain_level, "symptoms": symptoms, "level": level,
            "guidance": answer, "safety_warning": warning, "sources": sources}


if __name__ == "__main__":   # quick test:  py -m rag.guidance
    print(exercise_guidance("knee", 6, "stiffness, swelling")["guidance"])
