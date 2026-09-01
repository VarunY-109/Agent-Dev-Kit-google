"""YouTube Summarizer Agent.

A pure-Python ADK agent that takes a YouTube video URL, fetches its
auto-generated English captions, and produces a structured summary
with key points, timestamps and a TL;DR.

Tools:
    * ``extract_video_id`` - pull the 11-char video id from any
      youtube.com / youtu.be URL.
    * ``fetch_transcript``  - download the transcript via the
      public ``youtube-transcript-api`` if installed, otherwise
      fall back to a clearly-labelled "unavailable" response.
    * ``chunk_transcript``  - split the transcript into N roughly
      equal time windows for easier summarisation.
"""

import json
import re
import urllib.error
import urllib.request
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from google.adk.agents import Agent

# youtube-transcript-api is optional; the agent still loads if it's
# missing - it just can't fetch captions.
try:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    _YT_OK = True
except Exception:  # pragma: no cover - optional dependency
    YouTubeTranscriptApi = None  # type: ignore
    _YT_OK = False


# --- Helpers -----------------------------------------------------------------
_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com",
             "youtu.be", "www.youtu.be"}
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _extract_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host not in _YT_HOSTS:
        raise ValueError(f"Not a YouTube URL: {url!r}")
    if host.endswith("youtu.be"):
        return parsed.path.lstrip("/").split("/")[0]
    if parsed.path == "/watch":
        return parse_qs(parsed.query).get("v", [""])[0]
    if parsed.path.startswith("/embed/") or parsed.path.startswith("/shorts/"):
        return parsed.path.split("/")[2]
    raise ValueError(f"Could not parse video id from {url!r}")


# --- Tools -------------------------------------------------------------------
def extract_video_id(url: str) -> dict:
    """Extract the 11-character YouTube video id from a URL."""
    if not url or not url.strip():
        return {"status": "error", "error": "URL is required."}
    try:
        vid = _extract_id_from_url(url)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    if not _ID_RE.match(vid):
        return {"status": "error", "error": f"Invalid video id: {vid!r}"}
    return {
        "status": "ok",
        "video_id": vid,
        "watch_url": f"https://www.youtube.com/watch?v={vid}",
    }


def fetch_transcript(video_id: str, languages: str = "en") -> dict:
    """Fetch the transcript (captions) for a YouTube video.

    Args:
        video_id:  11-character YouTube video id.
        languages: Comma-separated list of preferred languages
                   (default ``"en"``).

    Notes:
        Requires the ``youtube-transcript-api`` package:
        ``pip install youtube-transcript-api``. If it isn't
        installed, the tool returns a clearly-labelled error.
    """
    if not _ID_RE.match(video_id or ""):
        return {"status": "error", "error": "Invalid video id."}
    if not _YT_OK:
        return {
            "status": "error",
            "error": (
                "youtube-transcript-api is not installed. Run "
                "`pip install youtube-transcript-api` and try again."
            ),
        }

    langs = [lang.strip() for lang in languages.split(",") if lang.strip()]
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
    except Exception as exc:  # noqa: BLE001 - library raises varied errors
        return {"status": "error", "error": f"Transcript fetch failed: {exc}"}

    # Convert to a compact list of {start, duration, text} dicts.
    text = " ".join(seg.get("text", "").replace("\n", " ") for seg in segments).strip()
    return {
        "status": "ok",
        "video_id": video_id,
        "languages": langs,
        "segment_count": len(segments),
        "transcript": text,
        "segments": [
            {"start": round(seg.get("start", 0.0), 2),
             "duration": round(seg.get("duration", 0.0), 2),
             "text": seg.get("text", "").strip()}
            for seg in segments
        ],
    }


def chunk_transcript(segments_json: str, chunks: int = 5) -> dict:
    """Split a transcript (JSON string) into N roughly equal time windows.

    Args:
        segments_json: The ``segments`` list returned by
            ``fetch_transcript``, serialised as JSON.
        chunks:       Number of chunks to produce (default 5).
    """
    try:
        segments = json.loads(segments_json)
    except (TypeError, ValueError) as exc:
        return {"status": "error", "error": f"Invalid JSON: {exc}"}
    if not isinstance(segments, list) or not segments:
        return {"status": "error", "error": "No segments to chunk."}

    chunks_n = max(1, min(int(chunks), 50))
    total_duration = max(
        seg.get("start", 0) + seg.get("duration", 0) for seg in segments
    )
    if total_duration <= 0:
        return {"status": "error", "error": "Segments have no timing data."}

    bucket_size = total_duration / chunks_n
    buckets: List[List[Dict]] = [[] for _ in range(chunks_n)]
    for seg in segments:
        idx = min(int(seg.get("start", 0) / bucket_size), chunks_n - 1)
        buckets[idx].append(seg)

    out = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        start = bucket[0].get("start", 0.0)
        end = bucket[-1].get("start", 0.0) + bucket[-1].get("duration", 0.0)
        text = " ".join(seg.get("text", "").strip() for seg in bucket).strip()
        out.append({
            "index": i + 1,
            "start_seconds": round(start, 2),
            "end_seconds": round(end, 2),
            "text": text,
        })
    return {"status": "ok", "chunk_count": len(out), "chunks": out}


# --- Agent definition ---------------------------------------------------------
root_agent = Agent(
    name="youtube_summarizer_agent",
    model="gemini-2.0-flash",
    description=(
        "Fetches a YouTube video's transcript and produces a "
        "structured summary with timestamps."
    ),
    instruction="""
    You are a video-summarisation assistant.

    WORKFLOW:
    1. When the user shares a YouTube URL, first call
       `extract_video_id` to normalise it.
    2. Call `fetch_transcript` with the resolved video id.
    3. If the transcript is long, call `chunk_transcript` with
       chunks=5 to break it into time windows.
    4. Read each chunk and produce:
         * A 2-3 sentence TL;DR.
         * 5-7 bullet key points.
         * A short "Notable quotes" list (verbatim, with timestamp).
         * A "Timestamps" map of key topic -> seconds-since-start.

    RULES:
    - Cite timestamps as `mm:ss` (e.g. 02:35).
    - If the transcript is unavailable, say so honestly and suggest
       the user paste a summary manually.
    - Never invent quotes; only quote what is actually in the text.
    """,
    tools=[extract_video_id, fetch_transcript, chunk_transcript],
)
