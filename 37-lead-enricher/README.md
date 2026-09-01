# Lead Enrichment Agent

A pure-Python ADK agent that turns a sparse lead (name + company,
or just a domain) into a **structured profile** with industry
guess, company size bucket, tech-stack hints, recent press
mentions, and a 0-100 lead score.

## Tools

| Tool | Purpose |
| --- | --- |
| `normalize_domain(input)` | Clean up domain/URL. |
| `fetch_homepage(domain)` | Download + strip HTML. |
| `guess_industry(text)` | saas / ecommerce / finance / ... |
| `detect_tech_stack(text)` | Match known tech names. |
| `guess_company_size(text)` | Headcount bucket. |
| `extract_recent_news(domain)` | Google News RSS top-5. |
| `lead_score(industry, tech, size, news)` | 0-100 composite. |
| `enrich(name, company, domain="")` | One-call pipeline. |

## Scoring Weights

| Signal | Max points |
| --- | --- |
| Industry identified | 25 |
| Tech stack detected | 25 |
| Company size 51-200 / 201-1000 / 1000+ | 25 |
| Recent press mentions | up to 25 |

75+ = `hot`, 50-74 = `warm`, <50 = `cold`.

## Project Structure

```
37-lead-enricher/
└── lead_enricher_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Disclaimer

Educational only. Respect `robots.txt` and the target site's terms
of service. The agent only fetches public homepages and a public
RSS feed.

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```
