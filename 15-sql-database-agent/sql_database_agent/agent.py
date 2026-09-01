"""SQL Database Agent.

A pure-Python ADK agent that converts natural-language questions into
SQL, runs them against a local SQLite database and explains the
results. The example ships with a tiny e-commerce sample database
(customers, products, orders) so it is fully runnable out of the box.

Tools:

* ``list_tables``         - discover the schema.
* ``describe_table``      - columns and types of a single table.
* ``run_sql``             - execute a SELECT query (read-only).
* ``seed_sample_database`` - (re)create the demo database on disk.
"""

import os
import sqlite3
from typing import Any, Dict, List

from google.adk.agents import Agent

DB_PATH = os.environ.get("SQLITE_DB_PATH", "sample.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _is_select_only(sql: str) -> bool:
    """Return True only for read-only SELECT/PRAGMA statements."""
    stripped = sql.strip().rstrip(";").lower()
    if not stripped:
        return False
    first = stripped.split(None, 1)[0]
    return first in {"select", "with", "pragma"}


def seed_sample_database() -> dict:
    """Create a small demo e-commerce database on disk.

    The function is idempotent: it drops and recreates the three demo
    tables (``customers``, ``products``, ``orders``) every time it is
    called. This makes it easy to reset the agent's world during
    experimentation.
    """
    schema_sql = """
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS customers;

    CREATE TABLE customers (
        id    INTEGER PRIMARY KEY,
        name  TEXT NOT NULL,
        email TEXT NOT NULL
    );

    CREATE TABLE products (
        id    INTEGER PRIMARY KEY,
        name  TEXT NOT NULL,
        price REAL NOT NULL
    );

    CREATE TABLE orders (
        id          INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        product_id  INTEGER NOT NULL REFERENCES products(id),
        quantity    INTEGER NOT NULL,
        ordered_at  TEXT    NOT NULL
    );
    """

    seed_rows = [
        ("INSERT INTO customers (id, name, email) VALUES (?, ?, ?)",
         [(1, "Alice", "alice@example.com"),
          (2, "Bob",   "bob@example.com"),
          (3, "Carol", "carol@example.com"),
          (4, "Dan",   "dan@example.com")]),

        ("INSERT INTO products (id, name, price) VALUES (?, ?, ?)",
         [(1, "Notebook",     4.50),
          (2, "Mechanical Pencil", 12.00),
          (3, "Coffee Mug",   9.95),
          (4, "Standing Desk", 249.00)]),

        ("INSERT INTO orders (id, customer_id, product_id, quantity, ordered_at) "
         "VALUES (?, ?, ?, ?, ?)",
         [(1, 1, 1, 3, "2026-08-01"),
          (2, 1, 3, 1, "2026-08-04"),
          (3, 2, 2, 2, "2026-08-05"),
          (4, 3, 4, 1, "2026-08-10"),
          (5, 3, 1, 5, "2026-08-15"),
          (6, 4, 3, 4, "2026-08-22")]),
    ]

    with _connect() as conn:
        conn.executescript(schema_sql)
        for sql, params in seed_rows:
            conn.executemany(sql, params)
        conn.commit()

    return {
        "status": "ok",
        "message": f"Demo database recreated at '{DB_PATH}'.",
        "tables": ["customers", "products", "orders"],
    }


def list_tables() -> dict:
    """List every user table in the SQLite database."""
    if not os.path.exists(DB_PATH):
        seed_sample_database()

    with _connect() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [row["name"] for row in cur.fetchall()]
    return {"status": "ok", "tables": tables}


def describe_table(table_name: str) -> dict:
    """Return the column definitions of a table."""
    if not table_name or not table_name.replace("_", "").isalnum():
        return {"status": "error", "error": "Invalid table name."}

    sql = f"PRAGMA table_info({table_name})"
    with _connect() as conn:
        cur = conn.execute(sql)
        columns = [
            {"name": row["name"], "type": row["type"], "nullable": not row["notnull"]}
            for row in cur.fetchall()
        ]
    if not columns:
        return {"status": "error", "error": f"Table '{table_name}' not found."}
    return {"status": "ok", "table": table_name, "columns": columns}


def run_sql(query: str, limit: int = 25) -> dict:
    """Execute a read-only SQL query and return its rows.

    Args:
        query: A ``SELECT`` (or ``WITH``) SQL statement.
        limit: Maximum number of rows to return (default 25).

    Returns:
        A dict containing ``columns``, ``rows`` and ``row_count``.
    """
    if not query or not query.strip():
        return {"status": "error", "error": "Query cannot be empty."}

    if not _is_select_only(query):
        return {
            "status": "error",
            "error": "Only SELECT / WITH / PRAGMA statements are allowed.",
        }

    safe_limit = max(1, min(int(limit), 200))
    if "limit" not in query.lower():
        query = f"{query.rstrip(';')} LIMIT {safe_limit}"

    try:
        with _connect() as conn:
            cur = conn.execute(query)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows: List[List[Any]] = [list(row) for row in cur.fetchall()]
    except sqlite3.Error as exc:
        return {"status": "error", "error": f"SQLite error: {exc}"}

    return {
        "status": "ok",
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


root_agent = Agent(
    name="sql_database_agent",
    model="gemini-2.0-flash",
    description=(
        "Translates natural-language questions into read-only SQL "
        "against a local SQLite database and explains the results."
    ),
    instruction="""
    You are a careful data analyst who answers questions by querying a
    SQLite database.

    WORKFLOW:
    1. If you haven't already, call `seed_sample_database` once to
       create the demo e-commerce data.
    2. Call `list_tables` to discover available tables.
    3. Call `describe_table` for any table you intend to use.
    4. Write a single, read-only SQL statement that answers the
       user's question. Prefer explicit JOINs and avoid SELECT *.
    5. Call `run_sql` with that statement.
    6. Summarise the result in plain English and present the rows as
       a small table.

    RULES:
    - Only SELECT / WITH / PRAGMA queries are allowed - the tool
       will reject anything else.
    - If a query fails, read the SQLite error, fix the statement, and
       retry (up to 3 attempts).
    - Never invent data; if no rows are returned, say so explicitly.
    """,
    tools=[seed_sample_database, list_tables, describe_table, run_sql],
)
