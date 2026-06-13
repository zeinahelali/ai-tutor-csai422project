"""
tutor.py
High-level API for the AI Tutor.
Instantiate TutorSession to run conversations.
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from state import TutorState
from memory.memory_manager import (
    get_or_create_profile,
    create_session,
    update_session,
    end_session,
    save_profile,
)
from agents.graph import get_graph


class TutorSession:
    """
    Manages a single tutoring conversation.
    Handles state initialization, LangGraph invocation, and state persistence.
    """

    def __init__(self, student_id: str, name: str = "Student"):
        self.student_id = student_id
        self.name = name

        # Load or create persistent student profile
        self.profile = get_or_create_profile(student_id, name)
        self.profile["session_count"] = self.profile.get("session_count", 0) + 1

        # Create fresh session memory
        self.session = create_session(student_id)

        # Initialize full LangGraph state
        self.state: TutorState = {
            "next_agent": "supervisor",
            "intent": "",
            "messages": [],
            "user_input": "",
            "agent_response": "",
            "retrieved_chunks": [],
            "retrieval_needed": True,
            "retrieval_grounded": True,
            "student_profile": self.profile,
            "session_memory": self.session,
            "active_quiz": None,
            "awaiting_quiz_answer": False,
            "guardrail_triggered": False,
            "guardrail_type": None,
            "guardrail_message": None,
            "eval_metadata": {},
        }

        self.graph = get_graph()
        self._history: list[dict] = []

    def chat(self, user_input: str) -> str:
        """
        Send a message, run the LangGraph, return the tutor's response.
        """
        # Append user message to history
        self._history.append({"role": "user", "content": user_input})

        # Update state with the new user input and full history
        self.state = {
            **self.state,
            "user_input": user_input,
            "messages": [{"role": "user", "content": user_input}],
            "agent_response": "",
            "guardrail_triggered": False,
            "guardrail_type": None,
            "guardrail_message": None,
            "eval_metadata": {},
            # Pass current profile & session so nodes always see latest
            "student_profile": self.profile,
            "session_memory": self.session,
        }

        # Run the graph
        result = self.graph.invoke(self.state)

        # Sync back updated profile and session from result
        self.profile = result.get("student_profile", self.profile)
        self.session = result.get("session_memory", self.session)

        # Preserve quiz state across turns
        self.state = {
            **self.state,
            **result,
            "student_profile": self.profile,
            "session_memory": self.session,
        }

        response = result.get("agent_response", "I'm not sure how to respond to that.")
        self._history.append({"role": "assistant", "content": response})

        return response

    def end_session(self) -> str:
        """End the session, persist everything, return a goodbye message."""
        save_profile(self.profile)
        end_session(self.session["session_id"])
        return (
            f"Session ended. Your progress has been saved. "
            f"You've mastered: {', '.join(self.profile['topics_mastered']) or 'topics in progress'}. "
            f"Keep it up, {self.name}! 🎓"
        )

    @property
    def history(self) -> list[dict]:
        return self._history


def quick_chat(student_id: str = "demo_student", name: str = "Demo Student"):
    """
    Simple CLI loop for testing without the Streamlit UI.
    """
    print(f"\n{'='*60}")
    print(f"  AI {__import__('config').SUBJECT} Tutor — {__import__('config').SUBJECT_CODE}")
    print(f"{'='*60}")
    print(f"  Student: {name}  |  ID: {student_id}")
    print("  Type 'quit' to exit, 'summary' for a session summary.")
    print(f"{'='*60}\n")

    session = TutorSession(student_id=student_id, name=name)

    greeting = session.chat("Hello! What can you help me with today?")
    print(f"Tutor: {greeting}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print(f"\nTutor: {session.end_session()}")
            break

        response = session.chat(user_input)
        print(f"\nTutor: {response}\n")


if __name__ == "__main__":
    quick_chat()
