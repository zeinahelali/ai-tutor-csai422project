"""
evaluation/evaluator.py — Full evaluation suite using Groq (free).
"""
from __future__ import annotations

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from utils.llm import get_llm

from config import EVAL_LOG_PATH, SUBJECT
from rag.pipeline import naive_retrieve, advanced_retrieve, get_vectorstore


def LLM():
    return get_llm(temperature=0)


# ── 1. RAGAS-style faithfulness ───────────────────────────────────────────────

FAITHFULNESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an evaluator for a RAG tutoring system. "
     "Assess whether the tutor's answer is grounded in the retrieved context. "
     "Score from 0.0 (hallucinated) to 1.0 (fully supported). "
     'Reply ONLY with JSON: {"score": 0.0-1.0, "reasoning": "brief"}'),
    ("human", "Question: {question}\n\nContext:\n{context}\n\nTutor answer:\n{answer}"),
])

CONTEXT_PRECISION_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are evaluating retrieval quality for a tutoring system. "
     "For each chunk, determine if it is relevant to the question. "
     "Precision = relevant_chunks / total_chunks. "
     'Reply ONLY with JSON: {"precision": 0.0-1.0, "relevant_count": int, "total_count": int}'),
    ("human", "Question: {question}\n\nChunks:\n{chunks}"),
])


def evaluate_faithfulness(question: str, context_chunks: list[dict], answer: str) -> dict:
    context = "\n\n".join(f"[{i+1}] {c['source']}: {c['content'][:400]}"
                          for i, c in enumerate(context_chunks))
    try:
        import re
        response = LLM().invoke(
            FAITHFULNESS_PROMPT.format_messages(question=question, context=context, answer=answer)
        )
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        return json.loads(match.group()) if match else {"score": 0.5}
    except Exception as e:
        return {"score": 0.0, "reasoning": str(e)}


def evaluate_context_precision(question: str, chunks: list[dict]) -> dict:
    chunks_text = "\n\n".join(f"[{i+1}] {c['source']}: {c['content'][:300]}"
                               for i, c in enumerate(chunks))
    try:
        import re
        response = LLM().invoke(
            CONTEXT_PRECISION_PROMPT.format_messages(question=question, chunks=chunks_text)
        )
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        return json.loads(match.group()) if match else {"precision": 0.5}
    except Exception as e:
        return {"precision": 0.0, "error": str(e)}


# ── 2. Pedagogical compliance ─────────────────────────────────────────────────

PED_COMPLIANCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a pedagogical compliance judge for an AI tutoring system. "
     "If the student asked for a direct answer/code, the tutor MUST give a hint only — not the solution. "
     "If the student asked a genuine conceptual question, full explanation is fine. "
     'Reply ONLY with JSON: {"compliant": true/false, "violation_type": null or "gave_direct_answer" or "refused_legitimate_question", "confidence": 0.0-1.0}'),
    ("human", "Student message: {student_message}\n\nTutor response: {tutor_response}"),
])


def evaluate_pedagogical_compliance(student_message: str, tutor_response: str) -> dict:
    try:
        import re
        response = LLM().invoke(
            PED_COMPLIANCE_PROMPT.format_messages(
                student_message=student_message, tutor_response=tutor_response)
        )
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        return json.loads(match.group()) if match else {"compliant": True, "confidence": 0.5}
    except Exception as e:
        return {"compliant": True, "error": str(e)}


# ── 3. Misconception detection ────────────────────────────────────────────────

MISCONCEPTION_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Evaluate whether the detected misconception accurately describes the student's error. "
     "Detected: '{detected}'. Correct answer: '{correct_answer}'. Student answer: '{student_answer}'. "
     'Reply ONLY with JSON: {"accurate": true/false, "reasoning": "brief"}'),
    ("human", "Is the detected misconception accurate?"),
])


def evaluate_misconception_detection(student_answer: str, correct_answer: str,
                                      detected_misconception: Optional[str]) -> dict:
    if not detected_misconception:
        return {"accurate": True, "note": "no misconception detected"}
    try:
        import re
        response = LLM().invoke(
            MISCONCEPTION_JUDGE_PROMPT.format_messages(
                detected=detected_misconception, correct_answer=correct_answer,
                student_answer=student_answer)
        )
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        return json.loads(match.group()) if match else {"accurate": True}
    except Exception as e:
        return {"accurate": False, "error": str(e)}


# ── 4. Naive vs Advanced RAG comparison ──────────────────────────────────────

def compare_rag_strategies(test_queries: list[str]) -> dict:
    vectorstore = get_vectorstore()
    results = []
    for query in test_queries:
        naive_chunks = naive_retrieve(vectorstore, query)
        adv_chunks, grounded = advanced_retrieve(vectorstore, query)
        naive_relevant = sum(1 for c in naive_chunks if c.get("score", 0) > 0.3)
        naive_prec = naive_relevant / max(len(naive_chunks), 1)
        adv_relevant = sum(1 for c in adv_chunks if c.get("score", 0) > 0.3)
        adv_prec = adv_relevant / max(len(adv_chunks), 1)
        results.append({
            "query": query,
            "naive_precision": naive_prec,
            "naive_avg_score": sum(c["score"] for c in naive_chunks) / max(len(naive_chunks), 1),
            "advanced_precision": adv_prec,
            "advanced_avg_score": sum(c["score"] for c in adv_chunks) / max(len(adv_chunks), 1),
            "advanced_grounded": grounded,
        })
    avg_naive = sum(r["naive_precision"] for r in results) / max(len(results), 1)
    avg_adv = sum(r["advanced_precision"] for r in results) / max(len(results), 1)
    improvement = avg_adv - avg_naive
    return {
        "per_query": results,
        "avg_naive_precision": round(avg_naive, 3),
        "avg_advanced_precision": round(avg_adv, 3),
        "precision_improvement": round(improvement, 3),
        "improvement_percent": round(improvement / max(avg_naive, 0.001) * 100, 1),
    }


# ── Full evaluation suite ─────────────────────────────────────────────────────

def run_full_evaluation() -> dict:
    print("=" * 60)
    print(f"Running Full Evaluation Suite — {SUBJECT} Tutor")
    print("=" * 60)

    print("\n[1/3] Comparing Naive vs Advanced RAG...")
    rag_queries = [
        "What is the time complexity of binary search tree operations?",
        "How does Floyd's cycle detection work?",
        "Explain dynamic programming memoization vs tabulation",
        "What are the types of tree traversal?",
        "How does a hash table handle collisions?",
        "What is the difference between a stack and a queue?",
        "Explain quicksort worst case scenario",
        "How do AVL trees self-balance?",
    ]
    rag_results = compare_rag_strategies(rag_queries)
    print(f"  Naive RAG avg precision:    {rag_results['avg_naive_precision']:.3f}")
    print(f"  Advanced RAG avg precision: {rag_results['avg_advanced_precision']:.3f}")
    print(f"  Improvement: {rag_results['improvement_percent']}%")

    print("\n[2/3] Testing Pedagogical Compliance...")
    compliance_tests = [
        {"student": "Can you just give me the answer to the two-sum problem?",
         "tutor": "I'd like to guide you! First, think about what data structure gives O(1) lookup..."},
        {"student": "Solve my homework: implement quicksort",
         "tutor": "Here's the complete quicksort: def quicksort(arr): ..."},
        {"student": "Explain how merge sort works",
         "tutor": "Merge sort is divide-and-conquer. It splits the array in half, recursively sorts each half..."},
        {"student": "Write the code for me for binary search",
         "tutor": "Let me give you a hint — what condition tells you when to stop searching?"},
    ]

    compliance_results = []
    for test in compliance_tests:
        result = evaluate_pedagogical_compliance(test["student"], test["tutor"])
        compliance_results.append({**test, "result": result})

    compliance_rate = sum(1 for r in compliance_results if r["result"].get("compliant", True)) / max(len(compliance_results), 1)
    print(f"  Pedagogical compliance rate: {compliance_rate:.1%}")

    print("\n[3/3] Testing Misconception Detection...")
    misconception_tests = [
        {"student_answer": "Linked lists are faster because they use less memory",
         "correct_answer": "Linked lists use MORE memory due to pointer overhead",
         "detected": "Student believes linked lists use less memory than arrays"},
        {"student_answer": "Quick sort is always O(n log n)",
         "correct_answer": "Quick sort is O(n²) worst case with bad pivot",
         "detected": "Student believes quicksort always runs in O(n log n)"},
        {"student_answer": "In-order traversal gives pre-sorted output",
         "correct_answer": "In-order traversal of a BST gives sorted ascending output",
         "detected": None},
    ]

    misconception_results = []
    for test in misconception_tests:
        result = evaluate_misconception_detection(
            test["student_answer"], test["correct_answer"], test.get("detected"))
        misconception_results.append({**test, "result": result})

    misc_accuracy = sum(1 for r in misconception_results if r["result"].get("accurate", True)) / max(len(misconception_results), 1)
    print(f"  Misconception detection accuracy: {misc_accuracy:.1%}")

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "subject": SUBJECT,
        "rag_comparison": rag_results,
        "pedagogical_compliance": {"rate": round(compliance_rate, 3), "tests": compliance_results},
        "misconception_detection": {"accuracy": round(misc_accuracy, 3), "tests": misconception_results},
        "summary": {
            "naive_rag_precision": rag_results["avg_naive_precision"],
            "advanced_rag_precision": rag_results["avg_advanced_precision"],
            "rag_improvement_pct": rag_results["improvement_percent"],
            "pedagogical_compliance_rate": round(compliance_rate, 3),
            "misconception_accuracy": round(misc_accuracy, 3),
        },
    }

    os.makedirs(os.path.dirname(EVAL_LOG_PATH), exist_ok=True)
    with open(EVAL_LOG_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Evaluation complete. Results saved to {EVAL_LOG_PATH}")
    print("\nSummary:")
    for k, v in report["summary"].items():
        print(f"  {k}: {v}")

    return report


if __name__ == "__main__":
    run_full_evaluation()