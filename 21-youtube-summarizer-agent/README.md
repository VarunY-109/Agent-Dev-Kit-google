# YouTube Summarizer Agent

A pure-Python ADK agent that takes a YouTube video URL, fetches its
auto-generated English captions, and produces a structured summary
with key points, notable quotes, and a `mm:ss` timestamp map.

## Tools

| Tool | Purpose |
| --- | --- |
| `extract_video_id(url)` | Parse the 11-char id from any `youtube.com` / `youtu.be` URL. |
| `fetch_transcript(video_id, languages="en")` | Download captions (requires `youtube-transcript-api`). |
| `chunk_transcript(segments_json, chunks=5)` | Slice the transcript into N time windows. |

> **Optional dependency** - `pip install youtube-transcript-api`.
> If the package is missing, the agent still loads and gracefully
> reports the limitation.

## Project Structure

```
21-youtube-summarizer-agent/
└── youtube_summarizer_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + transcript tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment and (optionally) install
   the transcript library:
   ```bash
   source ../.venv/bin/activate
   pip install youtube-transcript-api
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **youtube_summarizer_agent** from the dropdown.

## Example Prompts to Try

- "Summarise this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
- "Give me 5 key takeaways with timestamps from this talk."
- "Quote the most memorable line and tell me when it's said."
