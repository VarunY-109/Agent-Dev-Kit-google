# Contract Analyzer Agent

A pure-Python ADK agent that extracts parties, dates, obligations,
and risk flags from a free-form contract, and assigns a 0-100
risk score.

## Tools

| Tool | Purpose |
| --- | --- |
| `extract_dates(text)` | All date-like strings. |
| `extract_parties(text)` | Heuristic party extractor. |
| `extract_obligations(text, max_items=10)` | "shall / must / agrees to" sentences. |
| `detect_risk_flags(text)` | 10 common high-risk patterns. |
| `term(text)` | Term length (e.g. "3 years"). |
| `risk_score(flags_json)` | 0-100 score. |
| `analyze(text)` | One-call combined report. |

## Risk Patterns Tracked

| Flag | Why it matters |
| --- | --- |
| unlimited liability | Uncapped exposure |
| indemnification | One party bears the other's losses |
| auto-renew | Easy to miss a termination window |
| non-compete | Restricts future business |
| exclusivity | Locks you out of competing vendors |
| assignment without consent | Counterparty can transfer to anyone |
| liquidated damages | Pre-set penalty may be unenforceable |
| ip assignment | You may be giving up rights |
| unilateral termination | One-sided exit right |
| jurisdiction / venue | Where you'd have to litigate |

## Project Structure

```
36-contract-analyzer/
└── contract_analyzer_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Disclaimer

Educational only. Not legal advice. Always have a licensed attorney
review contracts before signing.

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```
