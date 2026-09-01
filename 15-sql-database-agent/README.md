# SQL Database Agent

A pure-Python ADK agent that lets users **ask questions in plain
English** about a SQLite database. The agent inspects the schema,
synthesises a `SELECT` statement, runs it, and explains the rows
that come back.

## Why SQLite?

SQLite ships with Python's standard library, so the example is
**zero-install**. The same `sqlite3` module would also let you point
the agent at any on-disk `.db` file - just set the
`SQLITE_DB_PATH` environment variable.

## Tools

| Tool | Purpose |
| --- | --- |
| `seed_sample_database()` | (Re)create a tiny e-commerce demo DB on disk. |
| `list_tables()` | List every user table. |
| `describe_table(name)` | Return column names + types for a table. |
| `run_sql(query, limit=25)` | Execute a read-only `SELECT` and return rows. |

Only `SELECT`, `WITH`, and `PRAGMA` statements are accepted -
anything else is rejected by the tool.

## Project Structure

```
15-sql-database-agent/
└── sql_database_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + SQL tools
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
4. Select **sql_database_agent** from the dropdown.

## Example Prompts to Try

- "Seed the demo database, then tell me how many orders each customer placed."
- "What is the total revenue per product, sorted from highest to lowest?"
- "Show me the 3 most recent orders with the customer name and product name."
- "What is the average order value?"
