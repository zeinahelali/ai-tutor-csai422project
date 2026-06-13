"""
state.py — Typed state schema for the LangGraph tutor graph.

Every node reads from and writes to a TutorState instance.
Using TypedDict keeps the graph compatible with LangGraph's state management.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
import operator


# ── Message type ──────────────────────────────────────────────────────────────
class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


# ── Student profile (persisted across sessions) ───────────────────────────────
class StudentProfile(TypedDict):
    student_id: str
    name: str
    level: Literal["beginner", "intermediate", "advanced"]
    topics_mastered: list[str]
    topics_struggling: list[str]
    quiz_scores: list[dict]          # [{topic, score, timestamp}]
    misconception_log: list[dict]    # [{topic, misconception, timestamp}]
    session_count: int
    total_hints_given: int


# ── Session memory (in-session only) ─────────────────────────────────────────
class SessionMemory(TypedDict):
    session_id: str
    current_topic: Optional[str]
    hint_count: int                  # hints given for current question
    questions_asked: list[str]       # questions the student asked this session
    concepts_covered: list[str]      # concepts explained this session
    quiz_results: list[dict]         # quiz results this session


# ── Main graph state ──────────────────────────────────────────────────────────
class TutorState(TypedDict):
    # Routing
    next_agent: str                  # which agent node runs next
    intent: str                      # classified intent of latest user message

    # Conversation
    messages: Annotated[list[Message], operator.add]   # append-only
    user_input: str
    agent_response: str

    # RAG
    retrieved_chunks: list[dict]     # [{content, source, score}]
    retrieval_needed: bool
    retrieval_grounded: bool         # CRAG: did retrieved docs answer the query?

    # Memory
    student_profile: StudentProfile
    session_memory: SessionMemory

    # Quiz state
    active_quiz: Optional[dict]      # {question, answer, topic, difficulty}
    awaiting_quiz_answer: bool

    # Guardrail flags
    guardrail_triggered: bool
    guardrail_type: Optional[str]    # "answer_withholding" | "scope" | "confidence"
    guardrail_message: Optional[str]

    # Evaluation tracking
    eval_metadata: dict[str, Any]    # logged per turn for the eval pipeline
