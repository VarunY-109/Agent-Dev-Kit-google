# Web Scraping Agent

A pure-Python ADK agent that can **fetch a public web page**, strip
its HTML down to readable text, and surface the paragraphs most
relevant to the user's question.

## Why stdlib Only?

The example intentionally avoids `requests`, `beautifulsoup4`,
`readability-lxml`, etc. Everything is built on:

* `urllib.request` for fetching
* `html.parser.HTMLParser` for HTML-to-text conversion

This makes the example **zero-install** beyond the ADK itself, and
shows how much you can do with just the standard library.

## Tools

| Tool | Purpose |
| --- | --- |
| `fetch_url(url, max_chars=8000)` | Download a page, extract its title, links and plaintext body. |
| `extract_text(text, query, max_paragraphs=5)` | Score paragraphs by keyword overlap and return the top hits. |

Only `http://` and `https://` URLs are accepted, and each fetch is
hard-capped at 1 MB to keep the agent safe to run.

## Project Structure

```
16-web-scraping-agent/
└── web_scraping_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + scraping tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **web_scraping_agent** from the dropdown.

## Example Prompts to Try

- "Fetch https://example.com and tell me what the page is about."
- "Read https://www.python.org/about/gettingstarted/ and summarise
  the 'Getting Started' steps."
- "Pull the page at https://en.wikipedia.org/wiki/Agentic_AI and list
  the 5 most-cited references."
