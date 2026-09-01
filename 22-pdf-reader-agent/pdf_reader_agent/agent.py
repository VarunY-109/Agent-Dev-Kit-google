"""PDF Reader Agent.

A pure-Python ADK agent that extracts text from a local PDF and lets
the user ask questions about it. The agent relies on ``pypdf`` for
parsing; if it isn't installed the tools return a clear error.

Tools:
    * ``pdf_info``         - page count, metadata, file size.
    * ``extract_pages``    - pull text for a page range.
    * ``search_pdf``       - case-insensitive keyword search across
                             the document, returning snippets and
                             page numbers.
"""

import os
from typing import Dict, List

try:
    from pypdf import PdfReader  # type: ignore
    _PYPDF_OK = True
except Exception:  # pragma: no cover - optional dependency
    try:
        from PyPDF2 import PdfReader  # type: ignore
        _PYPDF_OK = True
    except Exception:  # pragma: no cover
        PdfReader = None  # type: ignore
        _PYPDF_OK = False

from google.adk.agents import Agent

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
_SNIPPET_RADIUS = 120          # characters around each match


def _validate(path: str) -> Dict:
    if not path:
        return {"status": "error", "error": "path is required."}
    if not os.path.isfile(path):
        return {"status": "error", "error": f"File not found: {path!r}"}
    if not path.lower().endswith(".pdf"):
        return {"status": "error", "error": "Only .pdf files are supported."}
    size = os.path.getsize(path)
    if size > _MAX_BYTES:
        return {"status": "error", "error": f"PDF is {size} bytes; max is {_MAX_BYTES}."}
    if not _PYPDF_OK:
        return {
            "status": "error",
            "error": "pypdf is not installed. Run `pip install pypdf` and try again.",
        }
    return {"status": "ok", "size": size}


def pdf_info(path: str) -> dict:
    """Return basic metadata for a PDF file on disk."""
    ok = _validate(path)
    if ok["status"] != "ok":
        return ok

    reader = PdfReader(path)  # type: ignore[misc]
    meta = {}
    try:
        raw = reader.metadata or {}
        meta = {k.strip("/"): str(v) for k, v in raw.items()}
    except Exception:  # noqa: BLE001
        meta = {}

    return {
        "status": "ok",
        "path": os.path.abspath(path),
        "size_bytes": ok["size"],
        "page_count": len(reader.pages),
        "metadata": meta,
    }


def extract_pages(path: str, start_page: int = 1, end_page: int = 0) -> dict:
    """Extract text for a slice of pages (1-indexed, inclusive).

    Args:
        path:       Filesystem path to the PDF.
        start_page: First page to extract (default 1).
        end_page:   Last page to extract. 0 means "through the end".
    """
    ok = _validate(path)
    if ok["status"] != "ok":
        return ok

    reader = PdfReader(path)  # type: ignore[misc]
    total = len(reader.pages)
    start = max(1, int(start_page))
    end = int(end_page) if end_page else total
    end = min(end, total)
    if start > end:
        return {"status": "error", "error": "start_page > end_page."}

    pages: List[Dict] = []
    for i in range(start - 1, end):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            text = f"[error extracting page: {exc}]"
        pages.append({
            "page": i + 1,
            "char_count": len(text),
            "text": text,
        })
    return {
        "status": "ok",
        "path": os.path.abspath(path),
        "start_page": start,
        "end_page": end,
        "pages": pages,
    }


def search_pdf(path: str, query: str, max_results: int = 10) -> dict:
    """Find case-insensitive matches of ``query`` across the PDF.

    Each match includes the page number and a short snippet of
    surrounding text.
    """
    ok = _validate(path)
    if ok["status"] != "ok":
        return ok
    if not query or not query.strip():
        return {"status": "error", "error": "query is required."}

    reader = PdfReader(path)  # type: ignore[misc]
    needle = query.lower()
    max_n = max(1, min(int(max_results), 100))
    matches: List[Dict] = []

    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            continue
        lower = text.lower()
        start = 0
        while True:
            pos = lower.find(needle, start)
            if pos == -1:
                break
            s = max(0, pos - _SNIPPET_RADIUS)
            e = min(len(text), pos + len(needle) + _SNIPPET_RADIUS)
            matches.append({
                "page": idx,
                "offset": pos,
                "snippet": text[s:e].replace("\n", " "),
            })
            if len(matches) >= max_n:
                break
            start = pos + len(needle)
        if len(matches) >= max_n:
            break

    return {
        "status": "ok",
        "path": os.path.abspath(path),
        "query": query,
        "match_count": len(matches),
        "matches": matches,
    }


root_agent = Agent(
    name="pdf_reader_agent",
    model="gemini-2.0-flash",
    description=(
        "Reads a local PDF, extracts its text and answers "
        "questions about its content."
    ),
    instruction="""
    You are a document-analysis assistant for PDF files.

    WORKFLOW:
    1. When the user names a PDF, first call `pdf_info` to confirm
       the file exists and to learn the page count.
    2. For open-ended questions, call `extract_pages` over a small
       window (5-10 pages at a time) until you have enough context.
    3. For targeted lookups, call `search_pdf` first; it returns
       page numbers and snippets you can quote verbatim.
    4. Synthesise a clear answer. Always cite the page number
       (e.g. "p. 4") when quoting or asserting a fact.

    RULES:
    - Only quote text actually returned by the tools.
    - If extraction returns empty text, the page is likely
       image-only - tell the user and stop.
    - Respect the 50 MB file size cap.
    """,
    tools=[pdf_info, extract_pages, search_pdf],
)
