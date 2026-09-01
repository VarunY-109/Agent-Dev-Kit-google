# Retrieval-Augmented Generation (RAG) Agent

This example demonstrates a pure-Python **RAG agent** built with the
Agent Development Kit (ADK). The agent grounds every answer in a local
in-memory knowledge base, so responses are always backed by documents
the user has explicitly ingested.

## What is RAG?

Retrieval-Augmented Generation combines two steps:

1. **Retrieve** the most relevant chunks of text for a user's question.
2. **Generate** an answer with an LLM that is conditioned on the
   retrieved chunks.

This pattern reduces hallucinations because the model is forced to
cite real source material rather than rely solely on its parametric
knowledge.

## Tools

The agent exposes three Python tools:

| Tool | Purpose |
| --- | --- |
| `add_document(title, text)` | Ingest a document into the local store. |
| `search_knowledge_base(query, top_k=3)` | Return the most similar chunks using TF + cosine similarity. |
| `list_documents()` | List every document currently stored. |

> **Note** – The vector similarity is computed with pure-Python
> bag-of-words TF + cosine similarity, so no external embedding or
> vector database is required to run the example.

## Project Structure

```
13-rag-agent/
└── rag_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + tools definition
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate   # macOS/Linux
   ```
2. Copy `.env.example` to `.env` inside `rag_agent/` and set your
   `GOOGLE_API_KEY`.
3. From this directory, launch the ADK web UI:
   ```bash
   adk web
   ```
4. Select **rag_agent** from the dropdown.

## Example Prompts to Try

- "Add this document to your knowledge base: title='Intro to RAG',
  text='Retrieval-Augmented Generation combines retrieval and LLMs...'"
- "What is retrieval-augmented generation?"
- "List everything you know about."

After the first prompt ingests a document, the second prompt will be
answered using the retrieved snippet.
