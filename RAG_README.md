# RAG: personalized exercise guidance

The Colab notebook, converted to run inside this FastAPI backend.

| Notebook cell | File |
|---|---|
| Load PDFs + websites (PyPDFLoader, RecursiveUrlLoader, BeautifulSoup) | `rag/build_index.py` |
| Chunk (512 / 50) + embed (OpenAI) + Chroma | `rag/build_index.py`, saved to `chroma_db/` |
| Retrieve (k=4) + prompt + gpt-4o-mini | `rag/guidance.py` |
| `exercise_guidance(injury, pain_level, symptoms)` | `rag/guidance.py`, served by `routes/rag_routes.py` |

What changed from Colab:

- **API key:** read from a `.env` file instead of `userdata.get()`.
- **PDFs:** read from `data/pdfs/` instead of `/content/`.
- **Vector store:** saved to disk once, so each API call only retrieves and answers.
- **`!pip` lines:** moved to `requirements-rag.txt`.

## Setup (one time)

Run these from the Capstone_Backend folder in the VS Code terminal:

```
py -m pip install -r requirements-rag.txt
copy .env.example .env
notepad .env
```

In `.env`, put your key after `OPENAI_API_KEY=` and save. Then:

1. Save the two PDFs in `data\pdfs\` (names in `data\pdfs\PUT_PDFS_HERE.txt`).
2. Build the vector store: `py -m rag.build_index`. It crawls MedlinePlus and NIAMS, so it takes a few minutes.
3. Optional quick test: `py -m rag.guidance`.

## Use it

Start the server as usual (`py -m uvicorn main:app --reload`) and open http://127.0.0.1:8000/docs. The **RAG** section has:

- `POST /rag/guidance`: enter `injury_type`, `pain_level` (0-10) and `symptoms`.
- `POST /rag/guidance/injury/{injury_id}`: uses an injury saved with `POST /injury/submit`.

Both return the guidance text and the sources it came from.

Rebuild (`py -m rag.build_index`) whenever you add PDFs or want fresh website content. Keep `.env` private and don't submit it.
