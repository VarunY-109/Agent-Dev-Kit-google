# PDF Reader Agent

A pure-Python ADK agent that opens a local PDF, extracts its text,
and answers questions about it. The agent uses `pypdf` (or the
older `PyPDF2` if that's what's available) for parsing.

## Tools

| Tool | Purpose |
| --- | --- |
| `pdf_info(path)` | Page count, file size, document metadata. |
| `extract_pages(path, start_page=1, end_page=0)` | Pull text for a 1-indexed page range. |
| `search_pdf(path, query, max_results=10)` | Case-insensitive keyword search with snippets. |

> **Optional dependency** - `pip install pypdf`. If neither `pypdf`
> nor `PyPDF2` is installed, the tools return a clear error message.

## Project Structure

```
22-pdf-reader-agent/
└── pdf_reader_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + PDF tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment and install the parser:
   ```bash
   source ../.venv/bin/activate
   pip install pypdf
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **pdf_reader_agent** from the dropdown.

## Example Prompts to Try

- "Open /tmp/whitepaper.pdf and tell me what the document is about."
- "Search that PDF for 'latency' and quote the most relevant passage."
- "Summarise pages 3-7 of the report."
- "List the section headings in the first 10 pages."
