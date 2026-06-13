"""
rag/pipeline.py — RAG pipeline using Groq for LLM, local embeddings (free).
"""
from __future__ import annotations

import json
import os
import warnings
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    CHROMA_PERSIST_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K_RETRIEVAL,
    RERANK_TOP_N,
    SIMILARITY_THRESHOLD,
)
from utils.llm import get_llm


def _get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def _normalize_scores(chunks: list[dict]) -> list[dict]:
    """Normalize scores to 0-1 range using min-max normalization."""
    if not chunks:
        return chunks
    scores = [c["score"] for c in chunks]
    min_s, max_s = min(scores), max(scores)
    if max_s > min_s:
        for c in chunks:
            c["score"] = (c["score"] - min_s) / (max_s - min_s)
    else:
        for c in chunks:
            c["score"] = 1.0
    return chunks


def load_documents() -> list[Document]:
    materials_path = os.path.join(os.path.dirname(__file__), "../data/course_materials.json")
    if not os.path.exists(materials_path):
        raise FileNotFoundError(
            "Course materials not found. Run: python -m data.generate_course_materials"
        )
    with open(materials_path) as f:
        data = json.load(f)

    docs = []
    for item in data["materials"]:
        doc = Document(
            page_content=item["content"],
            metadata={
                "id": item["id"],
                "topic": item["topic"],
                "type": item["type"],
                "title": item["title"],
                "source": f"{item['topic']} — {item['title']}",
            },
        )
        docs.append(doc)
    return docs


def build_vector_store(force_rebuild: bool = False) -> Chroma:
    embeddings = _get_embeddings()
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

    if not force_rebuild and os.path.exists(os.path.join(CHROMA_PERSIST_DIR, "chroma.sqlite3")):
        print("Loading existing vector store...")
        return Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
            collection_name="tutor_kb",
        )

    print("Building vector store from course materials...")
    docs = load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    split_docs = splitter.split_documents(docs)
    print(f"  Split {len(docs)} documents into {len(split_docs)} chunks.")

    vectorstore = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name="tutor_kb",
    )
    print(f"  ✓ Vector store built with {len(split_docs)} chunks.")
    return vectorstore


def naive_retrieve(vectorstore: Chroma, query: str, k: int = TOP_K_RETRIEVAL) -> list[dict]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = vectorstore.similarity_search_with_relevance_scores(query, k=k)

    chunks = [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "score": float(score),
            "metadata": doc.metadata,
        }
        for doc, score in results
    ]
    return _normalize_scores(chunks)


def keyword_score(query: str, text: str) -> float:
    query_terms = set(query.lower().split())
    text_terms = text.lower().split()
    if not query_terms:
        return 0.0
    hits = sum(1 for t in text_terms if t in query_terms)
    return hits / (len(text_terms) ** 0.5 + 1e-6)


def hybrid_retrieve(vectorstore: Chroma, query: str, k: int = TOP_K_RETRIEVAL) -> list[dict]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dense_results = vectorstore.similarity_search_with_relevance_scores(query, k=k * 2)

    hybrid = []
    for doc, dense_score in dense_results:
        kw = keyword_score(query, doc.page_content)
        combined = 0.7 * float(dense_score) + 0.3 * kw
        hybrid.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "dense_score": float(dense_score),
            "keyword_score": kw,
            "score": combined,
            "metadata": doc.metadata,
        })

    hybrid = _normalize_scores(hybrid)
    hybrid.sort(key=lambda x: x["score"], reverse=True)
    return hybrid[:k]


def llm_rerank(query: str, chunks: list[dict], top_n: int = RERANK_TOP_N, llm=None) -> list[dict]:
    if llm is None:
        llm = get_llm(temperature=0)

    if len(chunks) <= top_n:
        return chunks

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a relevance ranking assistant for a Data Structures course tutor. "
         "Given a student query and a list of text chunks, rank the chunks by their relevance "
         "to answering the query. Return ONLY a JSON array of chunk indices (0-based), "
         "most relevant first, selecting the top {top_n} most useful chunks. "
         "Example output: [2, 0, 4]"),
        ("human",
         "Query: {query}\n\nChunks:\n{chunks_text}\n\nReturn top {top_n} indices as JSON array:"),
    ])

    chunks_text = "\n\n".join(
        f"[{i}] {c['source']}: {c['content'][:300]}..." for i, c in enumerate(chunks)
    )

    try:
        import re
        response = llm.invoke(
            prompt.format_messages(query=query, chunks_text=chunks_text, top_n=top_n)
        )
        match = re.search(r"\[[\d,\s]+\]", response.content)
        if match:
            indices = json.loads(match.group())
            reranked = [chunks[i] for i in indices if i < len(chunks)]
            for c in reranked:
                c["reranked"] = True
            return reranked[:top_n]
    except Exception as e:
        print(f"  Reranking failed ({e}), using score order.")

    return chunks[:top_n]


def grade_chunks(query: str, chunks: list[dict], llm=None) -> tuple[bool, list[dict]]:
    if llm is None:
        llm = get_llm(temperature=0)

    good_chunks = [c for c in chunks if c.get("score", 0) >= SIMILARITY_THRESHOLD]

    if not good_chunks:
        return False, []

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a retrieval grader for a Data Structures tutor. "
         "For each retrieved chunk, determine if it contains information relevant to "
         "answering the student's query. Reply with a JSON object: "
         '{"relevant_indices": [list of 0-based indices that are relevant], '
         '"overall_grounded": true/false}. '
         "Set overall_grounded=true if at least one chunk is relevant."),
        ("human", "Query: {query}\n\nChunks:\n{chunks_text}"),
    ])

    chunks_text = "\n\n".join(
        f"[{i}] {c['source']}: {c['content'][:400]}" for i, c in enumerate(good_chunks)
    )

    try:
        import re
        response = llm.invoke(prompt.format_messages(query=query, chunks_text=chunks_text))
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            relevant = [good_chunks[i] for i in result.get("relevant_indices", []) if i < len(good_chunks)]
            grounded = result.get("overall_grounded", len(relevant) > 0)
            return grounded, relevant
    except Exception:
        pass

    return len(good_chunks) > 0, good_chunks


def advanced_retrieve(
    vectorstore: Chroma,
    query: str,
    llm=None,
    use_reranking: bool = True,
) -> tuple[list[dict], bool]:
    chunks = hybrid_retrieve(vectorstore, query)

    if use_reranking:
        chunks = llm_rerank(query, chunks, llm=llm)

    is_grounded, graded_chunks = grade_chunks(query, chunks, llm=llm)

    return graded_chunks, is_grounded


_vectorstore: Optional[Chroma] = None


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = build_vector_store()
    return _vectorstore