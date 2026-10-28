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
    # Exercise handouts used with permission (not on GitHub, see .gitignore)
    "aaos-knee-conditioning.pdf",             # AAOS OrthoInfo Knee Conditioning Program
    "aaos-shoulder-conditioning.pdf",         # AAOS OrthoInfo Rotator Cuff and Shoulder Conditioning Program
    "wwl-low-back-level-1.pdf",               # WWL NHS Low Back Pain Exercises Level 1
    "wwl-low-back-level-2.pdf",               # WWL NHS Low Back Pain Exercises Level 2
    "wwl-low-back-level-3.pdf",               # WWL NHS Low Back Pain Exercises Level 3
    "wwl-neck-level-1.pdf",                   # WWL NHS Neck and Upper Back Exercises Level 1
    "wwl-neck-level-2.pdf",                   # WWL NHS Neck and Upper Back Exercises Level 2
    "wwl-neck-level-3.pdf",                   # WWL NHS Neck and Upper Back Exercises Level 3
]

WEBSITES = [
    {"url": "https://medlineplus.gov/bonesjointsandmuscles.html",
     "exclude_dirs": ["https://medlineplus.gov/spanish/"]},
    {"url": "https://www.niams.nih.gov/health-topics/",
     "exclude_dirs": ["https://www.niams.nih.gov/es/"]},
]

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-6-luna"


# Credit and disclaimer the publishers asked for (see their permission emails)
AAOS_CREDIT = ("Reproduced with permission from OrthoInfo © American Academy of Orthopaedic Surgeons. "
               "https://orthoinfo.org")
AAOS_DISCLAIMER = ("AAOS does not endorse any treatments, procedures, products, or physicians referenced herein. "
                   "This information is provided as an educational service and is not intended to serve as "
                   "medical advice. Anyone seeking specific orthopaedic advice or assistance should consult his "
                   "or her orthopaedic surgeon.")
WWL_CREDIT = "Exercise leaflets from Wrightington, Wigan and Leigh Teaching Hospitals NHS Foundation Trust, used with permission"


def check_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to the .env file in the Capstone_Backend folder.")
