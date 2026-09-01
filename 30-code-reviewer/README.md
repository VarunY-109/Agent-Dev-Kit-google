# Code Reviewer Agent

A multi-signal code reviewer that combines four pure-Python scans
(complexity, security, style, duplication) into a **scored,
prioritised** review with line numbers and fix suggestions.

## Tools

| Tool | Purpose |
| --- | --- |
| `detect_language(path)` | Map file extension to language. |
| `complexity_metrics(source)` | Per-function cyclomatic complexity. |
| `security_scan(source)` | Hard-coded secrets, `eval`/`exec`, `shell=True`. |
| `style_smells(source)` | Long lines, TODOs, missing docstrings. |
| `duplication_score(source)` | 6-line window duplicate ratio. |
| `score_review(metrics, security, smells)` | 0-100 aggregate. |
| `review(source, path)` | One-call all-in-one review. |

The agent is configured with `output_schema=ReviewReport` so its
final reply is guaranteed JSON shaped like:

```json
{
  "language": "python",
  "file": "snippet.py",
  "loc": 142,
  "function_count": 12,
  "avg_complexity": 3.2,
  "score": 78,
  "issues": [
    {"severity": "high", "line": 17, "rule": "SECRET",
     "message": "api_key = '...'", "suggestion": "Move to env."}
  ],
  "summary": "..."
}
```

## Project Structure

```
30-code-reviewer/
└── code_reviewer_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```

## Example Prompts

- "Review this Python function: ..."
- "Score this snippet for security risks."
- "What's the cyclomatic complexity of `process_orders` in this file?"
