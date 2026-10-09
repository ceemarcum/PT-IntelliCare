"""Shared settings for the RAG (converted from the Colab notebook)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent    # the Capstone_Backend folder

# In Colab this came from userdata.get(...). Here it comes from the .env file.
load_dotenv(BASE_DIR / ".env")

PDF_DIR = BASE_DIR / "data" / "pdfs"                   # was /content/ in Colab
CHROMA_DIR = BASE_DIR / "chroma_db"                    # the saved vector store

PDF_FILES = [
    "9789240071100-eng.pdf",                  # WHO Rehabilitation Module 2: Musculoskeletal
    "exercise-and-older-adults-nia_0.pdf",    # NIA Exercise and Physical Activity
]

WEBSITES = [
    {"url": "https://medlineplus.gov/bonesjointsandmuscles.html",
     "exclude_dirs": ["https://medlineplus.gov/spanish/"]},
    {"url": "https://www.niams.nih.gov/health-topics/",
     "exclude_dirs": ["https://www.niams.nih.gov/es/"]},
]

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


def check_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to the .env file in the Capstone_Backend folder.")
