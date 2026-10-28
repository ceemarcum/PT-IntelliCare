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

from rag.config import (CHROMA_DIR, EMBEDDING_MODEL, CHAT_MODEL, check_api_key, AAOS_CREDIT, AAOS_DISCLAIMER, WWL_CREDIT)
 
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
- Use exercises from the context below. If the context describes an exercise without a formal name, give it a short, specific name (for example "seated knee straightening", not "gentle knee exercise").
- Use the sets, reps or hold times from the context. If the context gives none for an exercise, write "amount: as advised by your physical therapist" instead of making numbers up.
- If the context has fewer than 3 exercises for this body part, add common, low-risk physical therapy exercises for it to reach 3, and put "(general suggestion, not from the sources)" after each one you add.
- If the context doesn't name movements to avoid, list 2 to 3 movements commonly limited for this injury and put "(general suggestion)" after each.
- Do not diagnose. If pain is 8/10 or higher, or there is numbness, tingling or inability to bear weight, add a final line advising them to see a doctor or physical therapist before exercising.

Context:
{context}

Question:
{question}

Answer:
"""

K = 8   # chunks retrieved per question

# Exercise handouts (used with permission), matched to the injury and level.
# The WWL leaflets come in Levels 1 to 3: beginner uses Level 1, and so on.
LEAFLET_LEVEL = {"beginner": "1", "intermediate": "2", "advanced": "3"}
HANDOUT_CHUNKS = 4   # chunks taken from the matching handout, on top of the normal search


def handout_for(injury, level=None):
    """The file name of the handout that fits this injury and level, or None."""
    injury = (injury or "").lower()
    n = LEAFLET_LEVEL.get(level, "1")
    if "knee" in injury:
        return "aaos-knee-conditioning.pdf"
    if "shoulder" in injury or "rotator" in injury:
        return "aaos-shoulder-conditioning.pdf"
    if "neck" in injury or "upper back" in injury:
        return f"wwl-neck-level-{n}.pdf"
    if "back" in injury or "spine" in injury or "lumbar" in injury:
        return f"wwl-low-back-level-{n}.pdf"
    return None


def file_name(chunk):
    return chunk.metadata.get("source", "").replace("\\", "/").rsplit("/", 1)[-1]


def is_handout(chunk):
    return file_name(chunk).startswith(("aaos-", "wwl-"))


_sources = None   # file name -> source path as stored in the index (filled on first use)


def handout_chunks(handout, query):
    """The handout's chunks that best match the query (searched only inside that handout)."""
    global _sources
    if _sources is None:
        stored = vectorstore.get(include=["metadatas"])["metadatas"]
        _sources = {m.get("source", "").replace("\\", "/").rsplit("/", 1)[-1]: m.get("source") for m in stored}
    source = _sources.get(handout)
    if not source:
        return []
    return vectorstore.similarity_search(query, k=HANDOUT_CHUNKS, filter={"source": source})

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
        llm = ChatOpenAI(model=CHAT_MODEL)


def rag_query(question, search_query=None, handout=None):
    """search_query: what to look up in the vector store (defaults to the question itself).
    handout: file name of the exercise handout for this injury and level (always searched)."""
    load()
    query = search_query or question
    chunks = handout_chunks(handout, query) if handout else []
    # the normal search, without other handouts (another body part or level would mislead the answer)
    for c in vectorstore.similarity_search(query, k=K * 2):
        if len(chunks) >= K:
            break
        if not is_handout(c) and c not in chunks:
            chunks.append(c)
    context = "\n\n---\n\n".join([c.page_content for c in chunks])
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    response = llm.invoke(prompt)
    # web pages keep their link; PDFs show the file name and page;
    # permission-only handouts show the credit their publisher asked for
    sources = []
    uses_aaos = False
    for c in chunks:
        src = c.metadata.get("source", "")
        name = file_name(c)   # file name, even for Windows paths on Cloud Run
        if name.startswith("aaos-"):
            uses_aaos = True
            src = AAOS_CREDIT
        elif name.startswith("wwl-"):
            src = WWL_CREDIT
        elif not src.startswith("http"):
            src = f"{name}, page {c.metadata.get('page', 0) + 1}"
        if src not in sources:
            sources.append(src)
    answer = response.content
    if uses_aaos:
        answer = f"{answer.rstrip()}\n\n{AAOS_DISCLAIMER}"
    return answer, sources


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
        answer, sources = rag_query(question, search_query, handout_for(injury, level))
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
