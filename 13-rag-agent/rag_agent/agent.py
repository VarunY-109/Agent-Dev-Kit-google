"""Retrieval-Augmented Generation (RAG) Agent.

A pure-Python ADK agent that grounds its answers in a small in-memory
knowledge base. The agent exposes three tools:

* `add_document`  - ingest a (title, text) document into the local store
* `search_knowledge_base` - retrieve the most relevant chunks for a query
* `list_documents` - list all ingested document titles

The vector similarity is computed with pure-Python bag-of-words cosine
similarity (no external embedding libraries required) so the example
runs out-of-the-box.
"""

import math
import re
from collections import Counter
from typing import Dict, List, Tuple

from google.adk.agents import Agent

_KNOWLEDGE_BASE: List[Dict] = []


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> List[str]:
    """Lowercase, alphanumeric tokenization."""
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _to_vector(tokens: Counter) -> Dict[str, float]:
    """Compute a TF (term-frequency) vector from a token counter."""
    total = sum(tokens.values()) or 1
    return {term: count / total for term, count in tokens.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    shared = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def add_document(title: str, text: str) -> dict:
    """Add a document to the in-memory knowledge base.

    Args:
        title: A short human-readable title for the document.
        text:  The full document body to ingest.

    Returns:
        A status dict confirming the ingestion.
    """
    if not title or not text:
        return {"status": "error", "message": "Both title and text are required."}

    tokens = Counter(_tokenize(text))
    _KNOWLEDGE_BASE.append(
        {"title": title, "text": text, "tokens": tokens}
    )
    return {
        "status": "ok",
        "message": f"Stored '{title}' ({len(tokens)} unique tokens).",
        "doc_count": len(_KNOWLEDGE_BASE),
    }


def search_knowledge_base(query: str, top_k: int = 3) -> dict:
    """Search the knowledge base for chunks relevant to ``query``.

    Args:
        query:  The user question or search phrase.
        top_k:  How many top results to return (default 3).

    Returns:
        A dict with the top matching documents and their similarity scores.
    """
    if not _KNOWLEDGE_BASE:
        return {"status": "empty", "results": []}

    if not query.strip():
        return {"status": "error", "message": "Query cannot be empty."}

    query_vec = _to_vector(Counter(_tokenize(query)))
    scored: List[Tuple[float, Dict]] = []
    for doc in _KNOWLEDGE_BASE:
        doc_vec = _to_vector(doc["tokens"])
        score = _cosine(query_vec, doc_vec)
        scored.append((score, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = scored[: max(1, int(top_k))]

    results = [
        {
            "title": doc["title"],
            "score": round(score, 4),
            "snippet": doc["text"][:240] + ("..." if len(doc["text"]) > 240 else ""),
        }
        for score, doc in top
        if score > 0
    ]

    return {"status": "ok", "results": results}


def list_documents() -> dict:
    """List every document currently in the knowledge base."""
    return {
        "status": "ok",
        "count": len(_KNOWLEDGE_BASE),
        "titles": [d["title"] for d in _KNOWLEDGE_BASE],
    }


root_agent = Agent(
    name="rag_agent",
    model="gemini-2.0-flash",
    description=(
        "Answers questions grounded in a local knowledge base using "
        "retrieval-augmented generation."
    ),
    instruction="""
    You are a Retrieval-Augmented Generation (RAG) assistant.

    WORKFLOW:
    1. When the user asks a question, ALWAYS start by calling
       `search_knowledge_base` with the user's query (top_k=3) to gather
       relevant context.
    2. If the knowledge base is empty, politely tell the user and offer
       to ingest documents via the `add_document` tool.
    3. Synthesize a clear, concise answer using ONLY the retrieved
       snippets. Cite document titles in square brackets, e.g. [Intro].
    4. If the retrieved context is insufficient, say so honestly rather
       than inventing facts.

    TOOLS AVAILABLE:
    - add_document: ingest a new (title, text) document
    - search_knowledge_base: semantic search over stored documents
    - list_documents: list everything currently stored

    Keep responses short, factual, and well-cited.
    """,
    tools=[add_document, search_knowledge_base, list_documents],
)
