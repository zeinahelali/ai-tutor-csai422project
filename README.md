# CSAI 422 — Option B: Personalized AI Tutor
**Data Structures (CSAI 230) — LangGraph Multi-Agent System**

---

## Overview
A production-grade, adaptive AI tutoring assistant for Data Structures that:
- **Personalizes** teaching to each learner's trajectory across multiple sessions
- **Never gives away answers** — enforces Socratic hint-first pedagogy
- **Grounds all explanations** in indexed course material via Advanced RAG (CRAG + Hybrid Search + LLM Reranking)
- **Tracks misconceptions** persistently and proactively addresses them
- **Evaluates itself** with RAGAS, LLM-as-judge, and pre/post quiz scoring

---

## Architecture

```
User Message
     │
     ▼
┌─────────────┐
│  Supervisor │  ← Intent classification & routing
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Guardrail  │  ← Answer withholding │ Scope enforcement │ Confidence calibration
└──────┬──────┘
       │  conditional routing
   ┌───┴────────────────────────────────┐
   │                                    │
   ▼                                    │
┌──────────────────┐         ┌──────────▼──────────┐
│ Curriculum       │         │    Explainer Agent   │
│ Planner Agent    │         │  (Advanced RAG +     │
│                  │         │   CRAG)              │
└──────────────────┘         └─────────────────────┘
                                         │
                             ┌───────────┴──────────┐
                             ▼                       ▼
                    ┌────────────────┐   ┌───────────────────────┐
                    │  Quiz Agent    │   │ Feedback Synthesizer   │
                    │ (gen+grade+    │   │ (session summary)      │
                    │  misconception)│   └───────────────────────┘
                    └────────────────┘
```

### Memory System
| Layer | Scope | Storage |
|-------|-------|---------|
| Session memory | Current conversation | In-RAM Python dict |
| Student profile | Across all sessions | JSON file (`data/memory.json`) |
| Misconception log | Persistent, structured | Inside student profile JSON |

### RAG Pipeline
1. **Naive RAG (baseline)**: Dense cosine similarity retrieval
2. **Advanced RAG**: Hybrid search (dense + keyword BM25-lite) → LLM reranking → CRAG grading
3. **CRAG fallback**: If retrieval confidence is low, adds a disclaimer rather than hallucinating

### Guardrails
| Type | Trigger | Behavior |
|------|---------|----------|
| Answer Withholding | "give me the answer / solve my homework" | Provide Socratic hint only |
| Scope Enforcement | Off-topic request (cooking, politics, etc.) | Redirect to Data Structures |
| Confidence Calibration | Low retrieval score / ungrounded retrieval | Append verification disclaimer |

---

## Setup

### 1. Clone and install
```bash
git clone <add your actual GitHub repo URL here>
cd ai_tutor
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free at console.groq.com)
# No OpenAI key needed — embeddings run locally via sentence-transformers
```

### 3. Generate course materials & build vector store
```bash
python -m data.generate_course_materials
python -c "from rag.pipeline import build_vector_store; build_vector_store()"
```

### 4. Run the Streamlit UI
```bash
streamlit run ui/app.py
```

### 5. Or use the CLI
```bash
python tutor.py
```

---

## Running Evaluations

```bash
# Full evaluation suite (RAGAS + LLM-as-judge + misconception detection)
python -m evaluation.evaluator

# Run tests
pytest tests/ -v
```

---

## Project Structure
```
ai_tutor/
├── config.py                  # All settings and constants
├── state.py                   # LangGraph TypedDict state schema
├── tutor.py                   # High-level TutorSession API + CLI runner
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── graph.py               # LangGraph StateGraph definition
│   └── nodes.py               # All 4 agent nodes + supervisor + guardrail
│
├── rag/
│   └── pipeline.py            # Naive RAG, Hybrid RAG, CRAG, vector store
│
├── memory/
│   └── memory_manager.py      # Session + persistent profile + misconception log
│
├── guardrails/
│   └── guardrails.py          # 3 guardrail classes (withholding, scope, confidence)
│
├── evaluation/
│   └── evaluator.py           # RAGAS, LLM-as-judge, pre/post delta, persona simulation
│
├── data/
│   ├── generate_course_materials.py   # Synthetic DS knowledge base + quiz bank
│   ├── course_materials.json          # (generated)
│   ├── memory.json                    # (generated, student profiles)
│   ├── eval_log.json                  # (generated, evaluation results)
│   └── chroma_db/                     # (generated, vector embeddings)
│
├── ui/
│   └── app.py                 # Streamlit chat UI + evaluation dashboard
│
└── tests/
    └── test_tutor.py          # Pytest suite (guardrails, memory, RAG, routing)
```

---

## Grading Self-Checklist
- [x] **Advanced RAG** — Hybrid search + LLM reranking + CRAG; baseline vs. advanced comparison
- [x] **Multiagent (LangGraph)** — 4 agents + supervisor orchestrator + conditional routing
- [x] **Memory** — Session memory (in-RAM) + student profile (JSON-persisted) + misconception log
- [x] **Guardrails** — Answer withholding, scope enforcement, confidence calibration
- [x] **Observability & Eval** — RAGAS faithfulness, context precision, pedagogical compliance (LLM-as-judge), misconception detection accuracy, 3 simulated student personas
- [x] **Tool Disclosure** — See below

---

## Tool Disclosure
| Tool | Purpose |
|------|---------|
| LangGraph | Multi-agent graph orchestration (required) |
| LangChain / langchain-core | LLM wrappers, prompt templates |
| langchain-text-splitters | RecursiveCharacterTextSplitter for RAG chunking |
| langchain-groq | Groq LLM integration (llama-3.1-8b-instant, free tier) |
| langchain-huggingface | HuggingFace embeddings integration |
| langchain-chroma | LangChain–ChromaDB bridge |
| ChromaDB | Vector store for RAG |
| Groq API (llama-3.1-8b-instant) | LLM backbone for all agents and evaluators (free tier, switched from OpenAI GPT-4o-mini after quota exhaustion) |
| sentence-transformers (all-MiniLM-L6-v2) | Local semantic embeddings for RAG (switched from OpenAI text-embedding-3-small; runs free on CPU) |
| RAGAS | Reference implementation for faithfulness/precision metrics |
| Streamlit | Chat UI and evaluation dashboard |
| Pytest | Unit + integration tests |
| Faker | (available for synthetic data extension) |
| Python-dotenv | Environment variable management |

All LLM usage was with an AI assistant (Claude). Every architectural decision, agent design,
and system prompt was authored and is fully understood by the team.
