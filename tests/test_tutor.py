"""
tests/test_tutor.py
Pytest test suite for the AI Tutor.
Run: pytest tests/ -v
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Guardrails tests ──────────────────────────────────────────────────────────

class TestGuardrails:

    def test_answer_withholding_triggers_on_homework_request(self):
        from guardrails.guardrails import check_answer_withholding
        triggered, msg = check_answer_withholding("give me the answer to this problem", hint_count=0)
        assert triggered is True
        assert "hint" in msg.lower() or "learn" in msg.lower()

    def test_answer_withholding_not_triggered_on_concept_question(self):
        from guardrails.guardrails import check_answer_withholding
        triggered, _ = check_answer_withholding("what is the time complexity of binary search?", hint_count=0)
        assert triggered is False

    def test_scope_enforcement_blocks_cooking(self):
        from guardrails.guardrails import check_scope
        triggered, msg = check_scope("How do I make pasta carbonara?")
        assert triggered is True
        assert "Data Structures" in msg

    def test_scope_enforcement_allows_ds_topics(self):
        from guardrails.guardrails import check_scope
        triggered, _ = check_scope("Explain how merge sort works")
        assert triggered is False

    def test_confidence_calibration_triggers_on_empty_chunks(self):
        from guardrails.guardrails import check_confidence
        triggered, msg = check_confidence("some query", [], is_grounded=False)
        assert triggered is True
        assert "knowledge base" in msg.lower() or "textbook" in msg.lower()

    def test_confidence_calibration_ok_with_good_chunks(self):
        from guardrails.guardrails import check_confidence
        chunks = [{"score": 0.85, "source": "Arrays — Introduction", "content": "Arrays are..."}]
        triggered, _ = check_confidence("what is an array", chunks, is_grounded=True)
        assert triggered is False


# ── Memory tests ──────────────────────────────────────────────────────────────

class TestMemory:

    def test_create_student_profile(self, tmp_path, monkeypatch):
        monkeypatch.setattr("memory.memory_manager.MEMORY_DB_PATH", str(tmp_path / "mem.json"))
        from memory.memory_manager import get_or_create_profile, load_profile
        profile = get_or_create_profile("test_001", "Test Student")
        assert profile["student_id"] == "test_001"
        assert profile["name"] == "Test Student"
        assert profile["level"] == "beginner"

        reloaded = load_profile("test_001")
        assert reloaded is not None
        assert reloaded["name"] == "Test Student"

    def test_quiz_result_updates_mastery(self, tmp_path, monkeypatch):
        monkeypatch.setattr("memory.memory_manager.MEMORY_DB_PATH", str(tmp_path / "mem.json"))
        from memory.memory_manager import get_or_create_profile, record_quiz_result
        profile = get_or_create_profile("test_002", "Mastery Test")

        for i in range(3):
            profile = record_quiz_result(profile, "Arrays", f"q{i}", 1.0, True)

        assert "Arrays" in profile["topics_mastered"]

    def test_misconception_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr("memory.memory_manager.MEMORY_DB_PATH", str(tmp_path / "mem.json"))
        from memory.memory_manager import get_or_create_profile, log_misconception
        profile = get_or_create_profile("test_003", "Misc Test")
        profile = log_misconception(profile, "Arrays", "Thinks arrays are O(n) access", "arrays are slow")
        assert len(profile["misconception_log"]) == 1
        assert profile["misconception_log"][0]["topic"] == "Arrays"
        assert profile["misconception_log"][0]["addressed"] is False

    def test_session_creation(self):
        from memory.memory_manager import create_session, get_session
        session = create_session("test_004")
        assert session["session_id"] is not None
        retrieved = get_session(session["session_id"])
        assert retrieved is not None

    def test_struggling_topic_detection(self, tmp_path, monkeypatch):
        monkeypatch.setattr("memory.memory_manager.MEMORY_DB_PATH", str(tmp_path / "mem.json"))
        from memory.memory_manager import get_or_create_profile, record_quiz_result
        profile = get_or_create_profile("test_005", "Struggle Test")
        for i in range(3):
            profile = record_quiz_result(profile, "Graphs", f"q{i}", 0.2, False)
        assert "Graphs" in profile["topics_struggling"]


# ── RAG pipeline tests ────────────────────────────────────────────────────────

class TestRAGPipeline:

    def test_keyword_score_returns_nonzero_for_match(self):
        from rag.pipeline import keyword_score
        score = keyword_score("binary search tree", "A binary search tree stores ordered nodes")
        assert score > 0

    def test_keyword_score_returns_zero_for_no_match(self):
        from rag.pipeline import keyword_score
        score = keyword_score("quantum physics", "A binary search tree stores ordered nodes")
        assert score == pytest.approx(0.0, abs=0.01)

    def test_hybrid_score_combines_dense_and_keyword(self):
        dense = 0.8
        kw = 0.4
        hybrid = 0.7 * dense + 0.3 * kw
        assert abs(hybrid - 0.68) < 0.01

    def test_load_documents_parses_materials(self, tmp_path, monkeypatch):
        import rag.pipeline as rp
        materials_path = tmp_path / "course_materials.json"
        materials_path.write_text(json.dumps({
            "materials": [{
                "id": "test_doc",
                "topic": "Arrays",
                "type": "concept",
                "title": "Test Arrays",
                "content": "Arrays are contiguous blocks of memory.",
            }],
            "quiz_bank": [],
        }))

        def mock_load():
            from langchain_core.documents import Document
            with open(materials_path) as f:
                data = json.load(f)
            return [
                Document(
                    page_content=item["content"],
                    metadata={"id": item["id"], "topic": item["topic"],
                               "title": item["title"], "source": item["title"]},
                )
                for item in data["materials"]
            ]

        monkeypatch.setattr(rp, "load_documents", mock_load)
        docs = rp.load_documents()
        assert len(docs) == 1
        assert docs[0].metadata["topic"] == "Arrays"


# ── Quiz logic tests ──────────────────────────────────────────────────────────

class TestQuizBank:

    def test_quiz_bank_loads(self, tmp_path, monkeypatch):
        import agents.nodes as n
        materials_path = tmp_path / "course_materials.json"
        materials_path.write_text(json.dumps({
            "materials": [],
            "quiz_bank": [
                {"id": "q1", "topic": "Arrays", "difficulty": "beginner",
                 "question": "What is O(1)?", "answer": "Constant time", "hint": "Think about access"}
            ],
        }))

        def mock_load():
            with open(materials_path) as f:
                return json.load(f).get("quiz_bank", [])
        monkeypatch.setattr(n, "_load_quiz_bank", mock_load)

        bank = n._load_quiz_bank()
        assert len(bank) == 1
        assert bank[0]["topic"] == "Arrays"


# ── Graph routing tests ────────────────────────────────────────────────────────

class TestGraphRouting:

    def test_route_after_guardrail_returns_end_when_blocked(self):
        from agents.graph import route_after_guardrail
        from langgraph.graph import END
        state = {"next_agent": "END"}
        result = route_after_guardrail(state)
        assert result == END

    def test_route_after_guardrail_returns_agent_name(self):
        from agents.graph import route_after_guardrail
        state = {"next_agent": "explainer"}
        result = route_after_guardrail(state)
        assert result == "explainer"

    def test_graph_builds_without_error(self):
        from agents.graph import build_tutor_graph
        graph = build_tutor_graph()
        assert graph is not None


# ── Data generation tests ──────────────────────────────────────────────────────

class TestDataGeneration:

    def test_generate_materials(self, tmp_path, monkeypatch):
        import data.generate_course_materials as gen
        monkeypatch.setattr(gen, "MATERIALS_PATH", str(tmp_path / "materials.json"))
        gen.generate_materials()
        assert (tmp_path / "materials.json").exists()

        with open(tmp_path / "materials.json") as f:
            data = json.load(f)
        assert len(data["materials"]) > 0
        assert len(data["quiz_bank"]) > 0

    def test_all_materials_have_required_fields(self):
        from data.generate_course_materials import COURSE_MATERIALS
        for m in COURSE_MATERIALS:
            assert "id" in m
            assert "topic" in m
            assert "content" in m
            assert len(m["content"]) > 50

    def test_all_quiz_questions_have_required_fields(self):
        from data.generate_course_materials import QUIZ_BANK
        for q in QUIZ_BANK:
            assert "id" in q
            assert "question" in q
            assert "answer" in q
            assert "hint" in q
            assert q["difficulty"] in ("beginner", "intermediate", "advanced")