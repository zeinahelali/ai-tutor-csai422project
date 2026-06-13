"""
guardrails/guardrails.py
Three pedagogical guardrail classes:

1. Answer Withholding  — prevents giving direct homework solutions
2. Scope Enforcement   — keeps explanations within Data Structures
3. Confidence Calibration — flags when the tutor is uncertain and avoids hallucination
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import OUT_OF_SCOPE_TOPICS, HINT_ONLY_TRIGGERS

from langchain_core.prompts import ChatPromptTemplate
from utils.llm import get_llm


# ── 1. Answer Withholding ─────────────────────────────────────────────────────

def check_answer_withholding(user_input: str, hint_count: int, max_hints: int = 3) -> tuple[bool, str]:
    lower = user_input.lower()
    triggered = any(trigger in lower for trigger in HINT_ONLY_TRIGGERS)

    if triggered and hint_count < max_hints:
        message = (
            "I'm here to help you learn, not just give you the answer! "
            "Let me give you a hint to guide your thinking instead. "
            f"You have {max_hints - hint_count} hints remaining before I show a worked example."
        )
        return True, message

    if triggered and hint_count >= max_hints:
        message = (
            "You've worked hard on this! After multiple hints, let me walk through "
            "a worked example — but try to understand each step rather than just copying it."
        )
        return True, message

    return False, ""


# ── 2. Scope Enforcement ──────────────────────────────────────────────────────

def check_scope(user_input: str, subject: str = "Data Structures") -> tuple[bool, str]:
    lower = user_input.lower()

    for topic in OUT_OF_SCOPE_TOPICS:
        if topic in lower:
            message = (
                f"I'm specialized in {subject} and can't help with {topic}. "
                f"I'm happy to discuss any Data Structures concept — "
                "arrays, trees, graphs, sorting, dynamic programming, and more!"
            )
            return True, message

    return False, ""


def llm_scope_check(user_input: str, subject: str = "Data Structures", llm=None) -> tuple[bool, str]:
    if llm is None:
        llm = get_llm(temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         f"You are a guardrail for a {subject} tutoring system. "
         "Determine if the student's message is within the scope of Data Structures "
         "(arrays, linked lists, stacks, queues, trees, graphs, heaps, hash tables, "
         "sorting algorithms, dynamic programming, algorithm complexity). "
         'Reply with JSON: {{"in_scope": true/false, "reason": "brief reason"}}'),
        ("human", "{query}"),
    ])

    try:
        import json, re
        response = llm.invoke(prompt.format_messages(query=user_input))
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if not result.get("in_scope", True):
                msg = (
                    f"That topic is outside my area of expertise ({subject}). "
                    "I focus on Data Structures and algorithm analysis. "
                    "Is there a related Data Structures concept I can help you with?"
                )
                return True, msg
    except Exception:
        pass

    return False, ""


# ── 3. Confidence Calibration ─────────────────────────────────────────────────

def check_confidence(
    query: str,
    retrieved_chunks: list[dict],
    is_grounded: bool,
    retrieval_score_threshold: float = 0.35,
) -> tuple[bool, str]:
    if not is_grounded or not retrieved_chunks:
        disclaimer = (
            "⚠️ I couldn't find specific material in my knowledge base about this exact question. "
            "My answer is based on general understanding and may not be fully accurate. "
            "I recommend consulting your textbook or course slides for authoritative information."
        )
        return True, disclaimer

    max_score = max((c.get("score", 0) for c in retrieved_chunks), default=0)
    if max_score < retrieval_score_threshold:
        disclaimer = (
            "ℹ️ I found some related material, but it may not perfectly match your question. "
            "Please verify with your course materials if anything seems off."
        )
        return True, disclaimer

    return False, ""


# ── Combined guardrail runner ─────────────────────────────────────────────────

def run_guardrails(
    user_input: str,
    retrieved_chunks: list[dict],
    is_grounded: bool,
    hint_count: int,
    llm=None,
) -> dict:
    # 1. Answer withholding
    withheld, wh_msg = check_answer_withholding(user_input, hint_count)
    if withheld:
        return {
            "triggered": True,
            "type": "answer_withholding",
            "message": wh_msg,
            "block_response": False,
        }

    # 2. Scope enforcement
    out_of_scope, scope_msg = check_scope(user_input)
    if out_of_scope:
        return {
            "triggered": True,
            "type": "scope",
            "message": scope_msg,
            "block_response": True,
        }

    # 3. Confidence calibration
    low_conf, conf_msg = check_confidence(user_input, retrieved_chunks, is_grounded)
    if low_conf:
        return {
            "triggered": True,
            "type": "confidence",
            "message": conf_msg,
            "block_response": False,
        }

    return {"triggered": False, "type": None, "message": None, "block_response": False}