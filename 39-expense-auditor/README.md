# Expense Auditor Agent

A pure-Python ADK agent that audits a list of expenses against a
configurable **company policy**, applies anomaly detection, and
returns per-item `approve / reject / review` decisions.

## Tools

| Tool | Purpose |
| --- | --- |
| `parse_csv_like(text)` | Best-effort CSV parser. |
| `policy_check(item, policy)` | Apply policy to one item. |
| `detect_anomalies(items_json)` | > 3σ from category mean. |
| `audit(items_json, policy)` | Per-item decisions + summary. |

## Policy Schema

```python
{
    "max_per_item": 500,
    "blocked_categories": ["alcohol", "gambling", "adult"],
    "require_receipt_above": 75,
    "weekend_block": False,
}
```

## Decision Rules

| Condition | Decision |
| --- | --- |
| Category is blocked | `reject` |
| Amount > per-item cap | `review` |
| Amount > receipt threshold and no receipt | `review` |
| Anomaly (> 3σ from category mean) | adds `anomaly` flag, escalates to `review` |
| Otherwise | `approve` |

## Project Structure

```
39-expense-auditor/
└── expense_auditor_agent/
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
