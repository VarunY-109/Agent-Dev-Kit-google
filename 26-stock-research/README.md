# Stock Research Agent

A multi-source equity-research agent that combines a price snapshot,
news sentiment, and peer comparison into a balanced report.

## Tools

| Tool | Purpose |
| --- | --- |
| `get_quote(ticker)` | Price, valuation ratios, 52w range, 6m return. |
| `get_news(ticker, limit=8)` | Recent Yahoo Finance headlines. |
| `sentiment_score(headlines_json)` | Lexicon-based positive/negative scoring. |
| `peer_comparison(ticker, peers="")` | Quick P/E + YTD comparison vs peers. |

> **Optional dependency** - `pip install yfinance` is required for
> `get_quote` and `peer_comparison`. The other tools work without it.

## Disclaimer

This agent is for **educational exploration only**. It is not
financial advice. Always do your own due diligence before investing.

## Project Structure

```
26-stock-research/
└── stock_research_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
pip install yfinance
cp .env.example .env
adk web
```

## Example Prompts

- "Research AAPL for me."
- "What's the sentiment on NVDA right now?"
- "Compare TSLA to F and GM."
