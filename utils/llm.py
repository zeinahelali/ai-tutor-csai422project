"""
utils/llm.py — Central LLM factory.
Returns a Groq ChatModel. All agents import from here instead of
instantiating ChatOpenAI directly.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_groq import ChatGroq
from config import GROQ_API_KEY, OPENAI_MODEL


def get_llm(temperature: float = 0.3):
    """Return a Groq LLM instance."""
    return ChatGroq(
        model=OPENAI_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=temperature,
    )
