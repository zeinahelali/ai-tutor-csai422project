"""
config.py — Central configuration for the AI Tutor system.
Configured to use Groq (free) for LLM, OpenAI for embeddings only.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM (Groq — free) ────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "dummy")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "llama-3.1-8b-instant")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ── Persistence ───────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
MEMORY_DB_PATH: str = os.getenv("MEMORY_DB_PATH", "./data/memory.json")
EVAL_LOG_PATH: str = "./data/eval_log.json"

# ── RAG settings ──────────────────────────────────────────────────────────────
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 150
TOP_K_RETRIEVAL: int = 5
RERANK_TOP_N: int = 3
SIMILARITY_THRESHOLD: float = 0.30

# ── Subject scope ─────────────────────────────────────────────────────────────
SUBJECT = "Data Structures"
SUBJECT_CODE = "CSAI 230"

# ── Guardrail keywords (scope enforcement) ────────────────────────────────────
OUT_OF_SCOPE_TOPICS = [
    "cooking", "pasta", "recipe", "food", "sports", "politics", "finance",
    "relationships", "medical", "legal advice", "hacking", "weapons",
    "carbonara", "bake", "fry", "cook",
]

# ── Pedagogical settings ──────────────────────────────────────────────────────
HINT_ONLY_TRIGGERS = [
    "give me the answer", "solve this for me", "write the code for",
    "do my homework", "complete this assignment", "just tell me the answer",
    "what is the answer to",
]
MAX_HINTS_BEFORE_ANSWER = 3

# ── Evaluation ────────────────────────────────────────────────────────────────
EVAL_JUDGE_MODEL: str = OPENAI_MODEL
MIN_RAGAS_FAITHFULNESS: float = 0.70