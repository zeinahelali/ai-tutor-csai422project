"""
agents/nodes.py — All agent nodes using Groq LLM (free).
"""
from __future__ import annotations

import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.prompts import ChatPromptTemplate
from utils.llm import get_llm

from config import SUBJECT, HINT_ONLY_TRIGGERS
from state import TutorState
from rag.pipeline import advanced_retrieve, get_vectorstore
from memory.memory_manager import (
    record_quiz_result,
    log_misconception,
    save_profile,
    get_session_summary,
)
from guardrails.guardrails import run_guardrails


def _llm(temperature: float = 0.3):
    return get_llm(temperature=temperature)


# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISOR NODE
# ─────────────────────────────────────────────────────────────────────────────

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a router for an AI Data Structures tutor. "
     "Classify the student's message into exactly one intent from this list: "
     "explain_concept, ask_quiz, answer_quiz, request_hint, request_summary, "
     "curriculum_check, out_of_scope, greeting. "
     "Reply with ONLY the intent string, no explanation."),
    ("human", "Student message: {message}"),
])


def supervisor_node(state: TutorState) -> TutorState:
    user_input = state["user_input"]

    # Pre-check 1: if a quiz is in progress, the next message is always an
    # answer. Check this before the LLM — free-text answers like "linked lists
    # use less memory" would otherwise be misclassified as explain_concept.
    if state.get("awaiting_quiz_answer"):
        intent = "answer_quiz"
        next_agent = "quiz"
    # Pre-check 2: hint-only triggers must route to explainer so the guardrail
    # can apply answer-withholding. Skip the LLM to avoid misclassification
    # as ask_quiz or answer_quiz.
    elif any(trigger in user_input.lower() for trigger in HINT_ONLY_TRIGGERS):
        intent = "explain_concept"
        next_agent = "explainer"
    else:
        llm = _llm(temperature=0)
        response = llm.invoke(INTENT_PROMPT.format_messages(message=user_input))
        intent = response.content.strip().lower()

        valid_intents = {
            "explain_concept": "explainer",
            "ask_quiz": "quiz",
            "answer_quiz": "quiz",
            "request_hint": "explainer",
            "request_summary": "feedback",
            "curriculum_check": "curriculum",
            "out_of_scope": "guardrail",
            "greeting": "explainer",
        }
        next_agent = valid_intents.get(intent, "explainer")

    return {
        **state,
        "intent": intent,
        "next_agent": next_agent,
        "eval_metadata": {
            **state.get("eval_metadata", {}),
            "intent": intent,
            "routed_to": next_agent,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GUARDRAIL NODE
# ─────────────────────────────────────────────────────────────────────────────

def guardrail_node(state: TutorState) -> TutorState:
    session = state.get("session_memory", {})
    hint_count = session.get("hint_count", 0)

    result = run_guardrails(
        user_input=state["user_input"],
        retrieved_chunks=state.get("retrieved_chunks", []),
        is_grounded=state.get("retrieval_grounded", True),
        hint_count=hint_count,
    )

    new_state = {
        **state,
        "guardrail_triggered": result["triggered"],
        "guardrail_type": result.get("type"),
        "guardrail_message": result.get("message"),
    }

    if result["triggered"] and result.get("block_response"):
        new_state["agent_response"] = result["message"]
        new_state["messages"] = [{"role": "assistant", "content": result["message"]}]
        new_state["next_agent"] = "END"

    return new_state


# ─────────────────────────────────────────────────────────────────────────────
# CURRICULUM PLANNER NODE
# ─────────────────────────────────────────────────────────────────────────────

CURRICULUM_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a Curriculum Planner for a {subject} tutor. "
     "The student's current level is {level}. "
     "Topics they have mastered: {mastered}. "
     "Topics they are struggling with: {struggling}. "
     "Concepts covered this session: {covered}. "
     "Suggest the most beneficial next learning step. Prioritize struggling topics. "
     "Format: 'Recommended next topic: <topic>\\nReason: <1-2 sentences>\\nSuggested approach: <how to proceed>'"),
    ("human", "{query}"),
])


def curriculum_planner_node(state: TutorState) -> TutorState:
    profile = state["student_profile"]
    session = state.get("session_memory", {})

    response = _llm().invoke(
        CURRICULUM_PROMPT.format_messages(
            subject=SUBJECT,
            level=profile.get("level", "beginner"),
            mastered=", ".join(profile.get("topics_mastered", [])) or "none yet",
            struggling=", ".join(profile.get("topics_struggling", [])) or "none",
            covered=", ".join(session.get("concepts_covered", [])) or "none this session",
            query=state["user_input"],
        )
    )

    answer = response.content.strip()
    return {
        **state,
        "agent_response": answer,
        "messages": [{"role": "assistant", "content": answer}],
        "next_agent": "END",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EXPLAINER NODE
# ─────────────────────────────────────────────────────────────────────────────

EXPLAINER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert {subject} tutor. The student's level is {level}. "
     "\n\nRelevant course material:\n{context}"
     "\n\nStudent misconceptions to address: {misconceptions}"
     "\n\nInstruction: {guardrail_instruction}"
     "\n\nTailor to level: beginner=simple analogies; intermediate=formal+examples; advanced=edge cases+tradeoffs. "
     "Never give away homework answers directly."),
    ("human", "{query}"),
])


def explainer_node(state: TutorState) -> TutorState:
    profile = state["student_profile"]
    user_input = state["user_input"]

    vectorstore = get_vectorstore()
    chunks, is_grounded = advanced_retrieve(vectorstore, user_input)

    context = "\n\n---\n\n".join(
        f"[{c['source']}]\n{c['content']}" for c in chunks
    ) if chunks else "No specific course material found for this query."

    unaddressed = [
        m["misconception"] for m in profile.get("misconception_log", [])
        if not m.get("addressed")
    ]
    misconceptions_str = "; ".join(unaddressed[-3:]) if unaddressed else "none"

    guardrail_triggered = state.get("guardrail_triggered", False)
    guardrail_type = state.get("guardrail_type")
    guardrail_msg = state.get("guardrail_message", "")

    if guardrail_triggered and guardrail_type == "answer_withholding":
        guardrail_instruction = (
            "Student asked for a direct answer. Give a Socratic hint ONLY — no full solution. "
            f"Start with: '{guardrail_msg}'"
        )
    else:
        guardrail_instruction = "Explain clearly and check understanding at the end."

    response = _llm(temperature=0.4).invoke(
        EXPLAINER_PROMPT.format_messages(
            subject=SUBJECT,
            level=profile.get("level", "beginner"),
            context=context,
            misconceptions=misconceptions_str,
            guardrail_instruction=guardrail_instruction,
            query=user_input,
        )
    )

    answer = response.content.strip()

    if not is_grounded:
        answer += (
            "\n\n⚠️ *Note: I couldn't find specific material in my knowledge base for this. "
            "Please verify with your course slides or textbook.*"
        )

    session = dict(state.get("session_memory", {}))
    if guardrail_triggered and guardrail_type == "answer_withholding":
        session["hint_count"] = session.get("hint_count", 0) + 1

    covered = list(session.get("concepts_covered", []))
    if chunks:
        topic = chunks[0].get("metadata", {}).get("topic", "")
        if topic and topic not in covered:
            covered.append(topic)
    session["concepts_covered"] = covered

    return {
        **state,
        "retrieved_chunks": chunks,
        "retrieval_grounded": is_grounded,
        "agent_response": answer,
        "session_memory": session,
        "messages": [{"role": "assistant", "content": answer}],
        "next_agent": "END",
        "eval_metadata": {
            **state.get("eval_metadata", {}),
            "retrieved_chunks": [{"source": c["source"], "score": c.get("score", 0)} for c in chunks],
            "is_grounded": is_grounded,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ NODE
# ─────────────────────────────────────────────────────────────────────────────

QUIZ_GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a {subject} quiz generator. Student level: {level}. "
     "Generate ONE quiz question about '{topic}'. "
     "Reply ONLY with valid JSON (no markdown): "
     '{{ "question": "...", "correct_answer": "...", "hint": "...", "topic": "...", "difficulty": "..." }}'),
    ("human", "Generate a {difficulty} question about {topic}."),
])

GRADING_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a {subject} quiz grader. "
     "Question: {question}. Correct answer: {correct_answer}. Student level: {level}. "
     "Reply ONLY with valid JSON: "
     '{{ "correct": true/false, "score": 0.0-1.0, "feedback": "...", '
     '"misconception": "short description if wrong, else null", "explanation": "..." }}'),
    ("human", "Student answer: {student_answer}"),
])


def quiz_node(state: TutorState) -> TutorState:
    profile = state["student_profile"]
    session = dict(state.get("session_memory", {}))
    intent = state.get("intent", "ask_quiz")

    if intent == "answer_quiz" and state.get("awaiting_quiz_answer") and state.get("active_quiz"):
        quiz = state["active_quiz"]
        grading_response = _llm(temperature=0).invoke(
            GRADING_PROMPT.format_messages(
                subject=SUBJECT,
                question=quiz["question"],
                correct_answer=quiz["answer"],
                level=profile.get("level", "beginner"),
                student_answer=state["user_input"],
            )
        )

        try:
            raw = re.search(r'\{.*\}', grading_response.content, re.DOTALL)
            grading = json.loads(raw.group()) if raw else {}
        except Exception:
            grading = {"correct": False, "score": 0.0, "feedback": "Could not parse answer.", "misconception": None}

        correct = grading.get("correct", False)
        score = float(grading.get("score", 1.0 if correct else 0.0))
        feedback = grading.get("feedback", "")
        misconception = grading.get("misconception")
        explanation = grading.get("explanation", "")

        profile = record_quiz_result(profile, topic=quiz.get("topic", "Unknown"),
                                     question_id=quiz.get("id", "unknown"), score=score, correct=correct)

        if misconception:
            profile = log_misconception(profile, topic=quiz.get("topic", "Unknown"),
                                        misconception=misconception, student_response=state["user_input"])

        quiz_results = list(session.get("quiz_results", []))
        quiz_results.append({"topic": quiz.get("topic"), "correct": correct, "score": score})
        session["quiz_results"] = quiz_results

        emoji = "✅" if correct else "❌"
        answer_text = f"{emoji} **{'Correct!' if correct else 'Not quite.'}** {feedback}\n\n**Explanation:** {explanation}"
        if misconception:
            answer_text += f"\n\n💡 *Misconception detected: {misconception}*"

        return {
            **state,
            "student_profile": profile,
            "session_memory": session,
            "agent_response": answer_text,
            "messages": [{"role": "assistant", "content": answer_text}],
            "active_quiz": None,
            "awaiting_quiz_answer": False,
            "next_agent": "END",
        }

    # Generate new quiz
    struggling = profile.get("topics_struggling", [])
    topic_keywords = ["arrays", "linked list", "stack", "queue", "tree", "bst",
                      "heap", "graph", "hash", "sorting", "dynamic programming", "avl"]
    inferred_topic = None
    for kw in topic_keywords:
        if kw in state["user_input"].lower():
            inferred_topic = kw.title()
            break

    topic = inferred_topic or (struggling[0] if struggling else session.get("current_topic") or "Arrays")
    difficulty = profile.get("level", "beginner")

    quiz_bank = _load_quiz_bank()
    asked = session.get("questions_asked", [])
    fresh = [q for q in quiz_bank if q["topic"].lower() == topic.lower()
             and q["difficulty"] == difficulty and q["id"] not in asked]

    if fresh:
        quiz_item = fresh[0]
        active_quiz = {"id": quiz_item["id"], "question": quiz_item["question"],
                       "answer": quiz_item["answer"], "hint": quiz_item.get("hint", ""),
                       "topic": quiz_item["topic"], "difficulty": quiz_item["difficulty"]}
    else:
        gen_response = _llm(temperature=0.6).invoke(
            QUIZ_GEN_PROMPT.format_messages(subject=SUBJECT, level=difficulty, topic=topic, difficulty=difficulty)
        )
        try:
            raw = re.search(r'\{.*\}', gen_response.content, re.DOTALL)
            q_data = json.loads(raw.group()) if raw else {}
        except Exception:
            q_data = {"question": "What is the time complexity of BST search?",
                      "correct_answer": "O(log n) average, O(n) worst case.",
                      "hint": "Think about how many nodes you visit.", "topic": topic, "difficulty": difficulty}

        active_quiz = {"id": f"gen_{topic}_{len(asked)}", "question": q_data.get("question", ""),
                       "answer": q_data.get("correct_answer", ""), "hint": q_data.get("hint", ""),
                       "topic": topic, "difficulty": difficulty}

    session["questions_asked"] = list(asked) + [active_quiz["id"]]
    session["current_topic"] = topic

    intro = f"📝 **Quiz — {topic} ({difficulty.title()}):**\n\n{active_quiz['question']}\n\n*Type your answer when ready.*"

    return {
        **state,
        "student_profile": profile,
        "session_memory": session,
        "agent_response": intro,
        "messages": [{"role": "assistant", "content": intro}],
        "active_quiz": active_quiz,
        "awaiting_quiz_answer": True,
        "next_agent": "END",
    }


def _load_quiz_bank() -> list[dict]:
    path = os.path.join(os.path.dirname(__file__), "../data/course_materials.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("quiz_bank", [])
    return []


# ─────────────────────────────────────────────────────────────────────────────
# FEEDBACK SYNTHESIZER NODE
# ─────────────────────────────────────────────────────────────────────────────

FEEDBACK_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a supportive {subject} tutor generating an end-of-session feedback report. "
     "Be encouraging but honest. Highlight progress and areas to review."),
    ("human", "Session summary:\n{summary}\n\nGenerate a personalized feedback report."),
])


def feedback_synthesizer_node(state: TutorState) -> TutorState:
    profile = state["student_profile"]
    session = state.get("session_memory", {})
    summary = get_session_summary(profile, session)
    response = _llm(temperature=0.5).invoke(
        FEEDBACK_PROMPT.format_messages(subject=SUBJECT, summary=summary)
    )
    answer = f"📊 **Session Feedback**\n\n{response.content.strip()}"
    return {
        **state,
        "agent_response": answer,
        "messages": [{"role": "assistant", "content": answer}],
        "next_agent": "END",
    }