# SQL Migrator Agent

A pure-Python ADK agent that reads a **SQLite** database, infers its
ER model, and produces a clean **PostgreSQL** or **MySQL** DDL
script with type-conversion table and foreign-key plan.

## Tools

| Tool | Purpose |
| --- | --- |
| `introspect_sqlite(path)` | Read tables, columns, indexes, FKs. |
| `translate_schema(intro_json, target)` | Emit target-dialect DDL. |
| `foreign_key_plan(intro_json, target)` | Generate ALTER TABLE statements. |
| `estimate_complexity(intro_json)` | Low/medium/high label. |

## Type Mapping (highlights)

| SQLite | PostgreSQL | MySQL |
| --- | --- | --- |
| INTEGER | BIGINT | BIGINT |
| REAL | DOUBLE PRECISION | DOUBLE |
| TEXT | TEXT | TEXT |
| BLOB | BYTEA | BLOB |
| BOOLEAN | BOOLEAN | TINYINT(1) |
| DATETIME | TIMESTAMP | DATETIME |

Unknown SQLite types are passed through as-is and flagged as a
manual review item.

## Project Structure

```
33-sql-migrator/
└── sql_migrator_agent/
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

- "Migrate /tmp/legacy.db to PostgreSQL."
- "What's the complexity of migrating app.db to MySQL?"
- "Generate the foreign-key plan for inventory.db as Postgres."
