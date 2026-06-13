"""
ui/app.py
Streamlit chat UI for the AI Tutor.
Run with: streamlit run ui/app.py
"""
import streamlit as st
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tutor import TutorSession
from config import SUBJECT, SUBJECT_CODE
from memory.memory_manager import get_or_create_profile

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"AI Tutor — {SUBJECT}",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --primary: #2D6BE4;
        --primary-light: #EBF1FD;
        --success: #16A34A;
        --warning: #D97706;
        --error: #DC2626;
        --surface: #F8FAFC;
        --border: #E2E8F0;
        --text: #1E293B;
        --text-muted: #64748B;
    }

    .stApp { font-family: 'Inter', sans-serif; }

    .chat-user {
        background: var(--primary);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0 8px 40px;
        font-size: 15px;
        line-height: 1.5;
    }

    .chat-tutor {
        background: var(--surface);
        color: var(--text);
        padding: 12px 16px;
        border-radius: 4px 18px 18px 18px;
        margin: 8px 40px 8px 0;
        border: 1px solid var(--border);
        font-size: 15px;
        line-height: 1.6;
    }

    .guardrail-badge {
        background: #FEF9C3;
        border: 1px solid #FDE047;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        color: #713F12;
        display: inline-block;
        margin-bottom: 6px;
    }

    .metric-card {
        background: white;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--primary);
    }

    .metric-label {
        font-size: 13px;
        color: var(--text-muted);
        margin-top: 4px;
    }

    .level-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .level-beginner { background: #DCFCE7; color: #15803D; }
    .level-intermediate { background: #FEF9C3; color: #92400E; }
    .level-advanced { background: #EDE9FE; color: #5B21B6; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

def init_session():
    if "tutor" not in st.session_state:
        st.session_state.tutor = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "student_id" not in st.session_state:
        st.session_state.student_id = None
    if "student_name" not in st.session_state:
        st.session_state.student_name = None
    if "eval_log" not in st.session_state:
        st.session_state.eval_log = []
    if "awaiting_quiz_answer" not in st.session_state:
        st.session_state.awaiting_quiz_answer = False
    if "active_quiz" not in st.session_state:
        st.session_state.active_quiz = None


init_session()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"### 📚 {SUBJECT_CODE}")
    st.markdown(f"**{SUBJECT} Tutor**")
    st.divider()

    if st.session_state.tutor is None:
        st.markdown("#### Start a Session")
        student_name = st.text_input("Your name", placeholder="e.g. Ahmed")
        student_id = st.text_input("Student ID", placeholder="e.g. s12345")

        if st.button("Start Learning →", use_container_width=True, type="primary"):
            if student_name and student_id:
                st.session_state.student_name = student_name
                st.session_state.student_id = student_id
                st.session_state.tutor = TutorSession(student_id=student_id, name=student_name)
                st.session_state.messages = []

                # Welcome message
                welcome = st.session_state.tutor.chat(
                    f"Hello! I'm {student_name}, let's get started with {SUBJECT}."
                )
                st.session_state.messages.append({"role": "assistant", "content": welcome})
                st.rerun()
            else:
                st.warning("Please enter both your name and student ID.")

    else:
        profile = st.session_state.tutor.profile
        session = st.session_state.tutor.session

        # Student info
        level = profile.get("level", "beginner")
        level_class = f"level-{level}"
        st.markdown(
            f"👋 **{profile['name']}**  "
            f"<span class='level-badge {level_class}'>{level.title()}</span>",
            unsafe_allow_html=True,
        )
        st.caption(f"Session #{profile.get('session_count', 1)}")
        st.divider()

        # Progress metrics
        mastered = profile.get("topics_mastered", [])
        struggling = profile.get("topics_struggling", [])
        quiz_scores = profile.get("quiz_scores", [])
        session_quizzes = session.get("quiz_results", [])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mastered", len(mastered))
        with col2:
            st.metric("Struggling", len(struggling))

        if quiz_scores:
            recent_avg = sum(q["score"] for q in quiz_scores[-5:]) / min(len(quiz_scores), 5)
            st.metric("Recent Quiz Avg", f"{recent_avg:.0%}")

        st.divider()

        # Topics
        if mastered:
            st.markdown("**✅ Mastered Topics:**")
            for t in mastered:
                st.markdown(f"- {t}")

        if struggling:
            st.markdown("**📌 Review These:**")
            for t in struggling:
                st.markdown(f"- {t}")

        st.divider()

        # Quick actions
        st.markdown("**Quick Actions:**")
        if st.button("📝 Quiz Me", use_container_width=True):
            topic = struggling[0] if struggling else "Arrays"
            response = st.session_state.tutor.chat(f"Quiz me on {topic}")
            st.session_state.messages.append({"role": "user", "content": f"Quiz me on {topic}"})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

        if st.button("📊 Session Summary", use_container_width=True):
            response = st.session_state.tutor.chat("Give me a summary of this session")
            st.session_state.messages.append({"role": "user", "content": "Session summary"})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

        if st.button("🗺️ What should I learn next?", use_container_width=True):
            response = st.session_state.tutor.chat("What should I study next based on my progress?")
            st.session_state.messages.append({"role": "user", "content": "What should I learn next?"})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

        st.divider()

        if st.button("End Session", use_container_width=True):
            goodbye = st.session_state.tutor.end_session()
            st.session_state.messages.append({"role": "assistant", "content": goodbye})
            st.session_state.tutor = None
            st.session_state.awaiting_quiz_answer = False
            st.session_state.active_quiz = None
            st.rerun()


# ── Main chat area ────────────────────────────────────────────────────────────

st.markdown(f"## 🎓 {SUBJECT} Tutor")

if st.session_state.tutor is None:
    # Landing state
    st.markdown(
        "Welcome! Start a session from the sidebar to begin learning. "
        "This tutor covers all core Data Structures topics with personalized pacing, "
        "quizzes, and Socratic guidance."
    )

    st.markdown("### What I can help you with:")
    topics = [
        ("🗃️", "Arrays & Dynamic Arrays"),
        ("🔗", "Linked Lists (Singly & Doubly)"),
        ("📚", "Stacks & Queues"),
        ("🌳", "Binary Trees & BSTs"),
        ("⚖️", "AVL Trees & Heaps"),
        ("🕸️", "Graphs & Shortest Paths"),
        ("🗝️", "Hash Tables"),
        ("🔀", "Sorting Algorithms"),
        ("💡", "Dynamic Programming"),
    ]
    cols = st.columns(3)
    for i, (icon, topic) in enumerate(topics):
        with cols[i % 3]:
            st.info(f"{icon} {topic}")

else:
    # Chat messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            content = msg["content"]
            st.markdown(f'<div class="chat-tutor">{content}</div>', unsafe_allow_html=True)

    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="Ask a question, request a quiz, or ask for a hint...",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button("Send →", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Restore quiz state into the tutor before invocation so the Quiz
        # Agent can tell the student is answering an existing question.
        st.session_state.tutor.state["awaiting_quiz_answer"] = st.session_state.awaiting_quiz_answer
        st.session_state.tutor.state["active_quiz"] = st.session_state.active_quiz

        with st.spinner("Thinking..."):
            response = st.session_state.tutor.chat(user_input)

        # Persist quiz state so it survives the next Streamlit rerun.
        st.session_state.awaiting_quiz_answer = st.session_state.tutor.state.get("awaiting_quiz_answer", False)
        st.session_state.active_quiz = st.session_state.tutor.state.get("active_quiz")

        state = st.session_state.tutor.state
        if state.get("guardrail_triggered"):
            badge = {
                "answer_withholding": "💡 Hint mode — keeping you in the driver's seat",
                "scope": "🚧 Out of scope",
                "confidence": "⚠️ Low confidence — please verify",
            }.get(state.get("guardrail_type", ""), "ℹ️ Guardrail active")
            response = f'<span class="guardrail-badge">{badge}</span>\n\n{response}'

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


# ── Eval Dashboard (expandable) ───────────────────────────────────────────────

eval_path = "./data/eval_log.json"
if os.path.exists(eval_path):
    with st.expander("📈 Evaluation Dashboard", expanded=False):
        with open(eval_path) as f:
            eval_data = json.load(f)

        summary = eval_data.get("summary", {})

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{summary.get("naive_rag_precision", 0):.2f}</div>'
                f'<div class="metric-label">Naive RAG Precision</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{summary.get("advanced_rag_precision", 0):.2f}</div>'
                f'<div class="metric-label">Advanced RAG Precision</div></div>',
                unsafe_allow_html=True,
            )
        with c3:
            rate = summary.get("pedagogical_compliance_rate", 0)
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{rate:.0%}</div>'
                f'<div class="metric-label">Pedagogical Compliance</div></div>',
                unsafe_allow_html=True,
            )
        with c4:
            acc = summary.get("misconception_accuracy", 0)
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{acc:.0%}</div>'
                f'<div class="metric-label">Misconception Detection</div></div>',
                unsafe_allow_html=True,
            )

        st.caption(f"Last evaluated: {eval_data.get('timestamp', 'N/A')}")
