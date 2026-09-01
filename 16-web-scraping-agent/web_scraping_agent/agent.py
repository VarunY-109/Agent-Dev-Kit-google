"""Web Scraping Agent.

A pure-Python ADK agent that can fetch a public web page, strip the
HTML down to readable text and surface the most relevant paragraphs
to the user. Everything is implemented with the Python standard
library - no third-party scraping libraries are required.

Tools:

* ``fetch_url`` - download a URL and return its title, links and a
  cleaned plaintext body.
* ``extract_text`` - keep only the paragraphs whose keyword
  relevance is above a threshold.
"""

import html
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List
from urllib.parse import urlparse

from google.adk.agents import Agent

# Restrict fetches to a reasonable size to avoid runaway downloads.
_MAX_BYTES = 1_000_000   # 1 MB
_TIMEOUT = 15            # seconds
_USER_AGENT = "ADK-WebScrapingAgent/1.0 (+https://example.com)"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_HREF_RE = re.compile(r"""<a\s+[^>]*href=["']([^"']+)["']""", re.IGNORECASE)


class _TextExtractor(HTMLParser):
    """Tiny HTML-to-text converter that preserves paragraph breaks."""

    BLOCK_TAGS = {
        "p", "div", "section", "article", "header", "footer",
        "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
        "br", "tr", "table",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: List[str] = []
        self._skip_depth = 0
        self._title = ""

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self._chunks.append("\n")
        if tag == "title":
            self._title = ""

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in self.BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        if self.get_starttag_text() and self.get_starttag_text().lower().startswith("<title"):
            self._title += data
        else:
            self._chunks.append(data)

    @property
    def text(self) -> str:
        return _WS_RE.sub(" ", "".join(self._chunks)).strip()

    @property
    def paragraphs(self) -> List[str]:
        raw = "".join(self._chunks)
        # Split on 2+ newlines, then collapse inner whitespace.
        blocks = re.split(r"\n{2,}", raw)
        return [
            _WS_RE.sub(" ", b).strip()
            for b in blocks
            if _WS_RE.sub(" ", b).strip()
        ]


# --- Helpers -----------------------------------------------------------------
def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return True


def _score(paragraph: str, keywords: List[str]) -> int:
    if not keywords:
        return 1
    lower = paragraph.lower()
    return sum(lower.count(kw) for kw in keywords)


# --- Tools -------------------------------------------------------------------
def fetch_url(url: str, max_chars: int = 8000) -> dict:
    """Download a web page and return a cleaned, summarised view.

    Args:
        url:       An ``http://`` or ``https://`` URL.
        max_chars: Soft cap on the returned plaintext (default 8000).

    Returns:
        A dict with ``title``, ``links``, ``text`` and ``paragraphs``.
    """
    if not _is_safe_url(url):
        return {"status": "error", "error": f"Disallowed URL: {url!r}"}

    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            raw = response.read(_MAX_BYTES)
            content_type = response.headers.get("Content-Type", "")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"Fetch failed: {exc}"}

    if "html" not in content_type.lower() and not url.lower().endswith(".html"):
        return {
            "status": "ok",
            "content_type": content_type,
            "text": raw[:max_chars].decode("utf-8", errors="replace"),
            "note": "Non-HTML content; returned raw bytes as text.",
        }

    parser = _TextExtractor()
    try:
        parser.feed(raw.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"HTML parse failed: {exc}"}

    paragraphs = parser.paragraphs[:200]
    text = "\n\n".join(paragraphs)
    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    links = list({m.group(1) for m in _HREF_RE.finditer(raw.decode("utf-8", errors="replace"))})[:50]

    return {
        "status": "ok",
        "url": url,
        "title": parser._title.strip() or url,
        "paragraph_count": len(paragraphs),
        "links": links,
        "text": text,
        "truncated": truncated,
    }


def extract_text(text: str, query: str = "", max_paragraphs: int = 5) -> dict:
    """Return the paragraphs of ``text`` that best match ``query``.

    Args:
        text:           The plaintext body to analyse.
        query:          Optional keywords to score paragraphs against.
        max_paragraphs: How many top paragraphs to return (default 5).

    Returns:
        A dict with the top-scoring paragraphs, in original order.
    """
    if not text or not text.strip():
        return {"status": "error", "error": "Empty input."}

    paragraphs = [p for p in re.split(r"\n{2,}", text) if p.strip()]
    keywords = [kw.strip().lower() for kw in re.split(r"\W+", query) if kw.strip()]

    scored = [(idx, _score(p, keywords), p) for idx, p in enumerate(paragraphs)]
    if keywords:
        scored.sort(key=lambda t: (t[1], -t[0]), reverse=True)
    top = sorted(scored[: max(1, int(max_paragraphs))], key=lambda t: t[0])

    return {
        "status": "ok",
        "matches": [
            {"index": idx, "score": score, "text": p}
            for idx, score, p in top
            if not keywords or score > 0
        ],
    }


# --- Agent definition ---------------------------------------------------------
root_agent = Agent(
    name="web_scraping_agent",
    model="gemini-2.0-flash",
    description=(
        "Fetches a public web page, strips it to readable text, and "
        "extracts the paragraphs most relevant to the user's question."
    ),
    instruction="""
    You are a research assistant that summarises web pages.

    WORKFLOW:
    1. When the user mentions a URL, call `fetch_url` first to
       download and clean the page.
    2. If the user has a specific question, immediately follow up
       with `extract_text`, passing the page's plaintext and the
       user's question as the query. This narrows the context to the
       most relevant paragraphs.
    3. Compose a concise, bullet-point summary in your own words.
    4. Always cite the source URL and the page title at the top of
       your reply.

    RULES:
    - Only fetch http(s) URLs that you can verify are public.
    - Hard cap on each fetch is 1 MB; respect the `truncated` flag.
    - If a page is non-HTML (PDF, JSON, image, ...), tell the user
       and stop.
    - Never follow links recursively; the user must explicitly ask.
    """,
    tools=[fetch_url, extract_text],
)
