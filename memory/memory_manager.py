"""
memory/memory_manager.py
Multi-layer memory system:
  - Session memory: in-RAM dict per session_id (cleared on session end)
  - Student profile memory: JSON-persisted across sessions
  - Misconception log: structured list inside the student profile
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MEMORY_DB_PATH
from state import StudentProfile, SessionMemory


# ── Persistence helpers ───────────────────────────────────────────────────────

def _load_db() -> dict:
    if os.path.exists(MEMORY_DB_PATH):
        with open(MEMORY_DB_PATH) as f:
            return json.load(f)
    return {"students": {}}


def _save_db(db: dict) -> None:
    os.makedirs(os.path.dirname(MEMORY_DB_PATH), exist_ok=True)
    with open(MEMORY_DB_PATH, "w") as f:
        json.dump(db, f, indent=2)


# ── Session memory (in-process only) ─────────────────────────────────────────

_sessions: dict[str, SessionMemory] = {}


def create_session(student_id: str) -> SessionMemory:
    session_id = str(uuid.uuid4())[:8]
    session: SessionMemory = {
        "session_id": session_id,
        "current_topic": None,
        "hint_count": 0,
        "questions_asked": [],
        "concepts_covered": [],
        "quiz_results": [],
    }
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[SessionMemory]:
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs) -> None:
    if session_id in _sessions:
        _sessions[session_id].update(kwargs)


def end_session(session_id: str) -> Optional[SessionMemory]:
    return _sessions.pop(session_id, None)


# ── Student profile (persistent) ──────────────────────────────────────────────

def get_or_create_profile(student_id: str, name: str = "Student") -> StudentProfile:
    db = _load_db()
    if student_id not in db["students"]:
        profile: StudentProfile = {
            "student_id": student_id,
            "name": name,
            "level": "beginner",
            "topics_mastered": [],
            "topics_struggling": [],
            "quiz_scores": [],
            "misconception_log": [],
            "session_count": 0,
            "total_hints_given": 0,
        }
        db["students"][student_id] = profile
        _save_db(db)
    return db["students"][student_id]


def load_profile(student_id: str) -> Optional[StudentProfile]:
    db = _load_db()
    return db["students"].get(student_id)


def save_profile(profile: StudentProfile) -> None:
    db = _load_db()
    db["students"][profile["student_id"]] = profile
    _save_db(db)


def record_quiz_result(
    profile: StudentProfile,
    topic: str,
    question_id: str,
    score: float,       # 0.0 – 1.0
    correct: bool,
) -> StudentProfile:
    """Persist a quiz result and update mastery / struggling lists."""
    profile["quiz_scores"].append({
        "topic": topic,
        "question_id": question_id,
        "score": score,
        "correct": correct,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Update mastery based on last 3 quizzes in this topic
    topic_results = [r for r in profile["quiz_scores"] if r["topic"] == topic][-3:]
    avg = sum(r["score"] for r in topic_results) / len(topic_results)

    if avg >= 0.8 and topic not in profile["topics_mastered"]:
        profile["topics_mastered"].append(topic)
        if topic in profile["topics_struggling"]:
            profile["topics_struggling"].remove(topic)
    elif avg < 0.5 and topic not in profile["topics_struggling"]:
        profile["topics_struggling"].append(topic)

    # Auto-adjust level
    mastered_count = len(profile["topics_mastered"])
    if mastered_count >= 5:
        profile["level"] = "advanced"
    elif mastered_count >= 2:
        profile["level"] = "intermediate"

    save_profile(profile)
    return profile


def log_misconception(
    profile: StudentProfile,
    topic: str,
    misconception: str,
    student_response: str,
) -> StudentProfile:
    """Add a structured misconception to the student's log."""
    profile["misconception_log"].append({
        "topic": topic,
        "misconception": misconception,
        "student_response": student_response[:200],
        "timestamp": datetime.utcnow().isoformat(),
        "addressed": False,
    })
    save_profile(profile)
    return profile


def mark_misconception_addressed(profile: StudentProfile, topic: str) -> StudentProfile:
    for m in profile["misconception_log"]:
        if m["topic"] == topic and not m["addressed"]:
            m["addressed"] = True
    save_profile(profile)
    return profile


def get_session_summary(profile: StudentProfile, session: SessionMemory) -> str:
    """Generate a human-readable session summary for the Feedback Synthesizer."""
    quiz_results = session.get("quiz_results", [])
    correct = sum(1 for r in quiz_results if r.get("correct"))
    total = len(quiz_results)
    topics = session.get("concepts_covered", [])

    lines = [
        f"Session Summary — {profile['name']} ({profile['level'].title()} level)",
        f"Topics covered: {', '.join(topics) if topics else 'None recorded'}",
        f"Quiz performance: {correct}/{total} correct" if total else "No quizzes taken this session.",
        f"Topics mastered overall: {', '.join(profile['topics_mastered']) or 'None yet'}",
        f"Topics to review: {', '.join(profile['topics_struggling']) or 'None identified'}",
    ]

    unaddressed = [m for m in profile["misconception_log"] if not m["addressed"]]
    if unaddressed:
        lines.append(f"Active misconceptions: {'; '.join(m['misconception'] for m in unaddressed[-3:])}")

    return "\n".join(lines)
