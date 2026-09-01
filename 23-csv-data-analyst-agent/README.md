# CSV Data Analyst Agent

A pure-Python ADK agent that loads a local CSV file into memory and
answers analytical questions about it. Everything is built on
Python's stdlib `csv` and `statistics` modules — no `pandas`
required.

## Tools

| Tool | Purpose |
| --- | --- |
| `load_csv(path)` | Read a CSV file, infer dtypes, cache the dataset. |
| `preview(path, n=5)` | Return the first N rows. |
| `column_stats(path, column)` | Count / mean / min / max / top-values. |
| `filter_rows(path, column, value, limit=50)` | Equality filter. |
| `group_by(path, group_column, target_column, agg)` | Group + aggregate (sum/mean/count/min/max). |

The cache is **per-process** (an in-memory dict). For multi-user or
multi-tenant use, swap the `_CACHE` dict for a session-scoped
backend.

## Project Structure

```
23-csv-data-analyst-agent/
└── csv_data_analyst_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + CSV tools
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
4. Select **csv_data_analyst_agent** from the dropdown.

## Example Prompts to Try

- "Load /tmp/sales.csv and tell me what columns it has."
- "What are the top 5 customers by total revenue?"
- "How many rows have status == 'returned'?"
- "Show me the average order value per region."
