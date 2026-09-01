"""SQL Migrator Agent.

Reads a SQLite schema, infers a logical ER model, and emits a
target-dialect CREATE TABLE script (PostgreSQL or MySQL) plus an
inventory of indexes, foreign keys, and required type conversions.
"""

import re
import sqlite3
from typing import Dict, List

from google.adk.agents import Agent


_TYPE_MAP_PG = {
    "INTEGER": "BIGINT", "INT": "BIGINT",
    "REAL": "DOUBLE PRECISION", "FLOAT": "DOUBLE PRECISION",
    "TEXT": "TEXT", "VARCHAR": "VARCHAR", "BLOB": "BYTEA",
    "BOOLEAN": "BOOLEAN", "DATETIME": "TIMESTAMP", "DATE": "DATE",
    "NUMERIC": "NUMERIC", "DECIMAL": "NUMERIC",
}

_TYPE_MAP_MYSQL = {
    "INTEGER": "BIGINT", "INT": "INT",
    "REAL": "DOUBLE", "FLOAT": "FLOAT",
    "TEXT": "TEXT", "VARCHAR": "VARCHAR(255)", "BLOB": "BLOB",
    "BOOLEAN": "TINYINT(1)", "DATETIME": "DATETIME", "DATE": "DATE",
    "NUMERIC": "DECIMAL(10,2)", "DECIMAL": "DECIMAL(10,2)",
}


def introspect_sqlite(path: str) -> dict:
    """Read a SQLite file and return its tables, columns, and indexes."""
    if not path:
        return {"status": "error", "error": "path is required."}
    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error as exc:
        return {"status": "error", "error": f"connect failed: {exc}"}
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
        schema = []
        for t in tables:
            cols = [{"name": r[1], "type": r[2], "notnull": bool(r[3]),
                     "default": r[4], "pk": bool(r[5])}
                    for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
            fks = [{"from": r[3], "to_table": r[2], "to_col": r[4]}
                   for r in conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()]
            idx = [r[1] for r in conn.execute(f"PRAGMA index_list({t})").fetchall()]
            schema.append({"table": t, "columns": cols, "foreign_keys": fks, "indexes": idx})
    finally:
        conn.close()
    return {"status": "ok", "path": path, "tables": schema, "table_count": len(schema)}


def _map_type(sqlite_type: str, target: str) -> str:
    base = (sqlite_type or "").split("(")[0].upper()
    table = _TYPE_MAP_PG if target == "postgres" else _TYPE_MAP_MYSQL
    return table.get(base, sqlite_type.upper())


def _emit_ddl(table: Dict, target: str) -> str:
    cols_sql = []
    pks = [c["name"] for c in table["columns"] if c["pk"]]
    for c in table["columns"]:
        line = f"    {c['name']} {_map_type(c['type'], target)}"
        if c["pk"]:
            line += " PRIMARY KEY" if len(pks) == 1 else ""
        if c["notnull"] and not c["pk"]:
            line += " NOT NULL"
        if c["default"] is not None:
            line += f" DEFAULT {c['default']}"
        cols_sql.append(line)
    if len(pks) > 1 and target == "postgres":
        cols_sql.append(f"    PRIMARY KEY ({', '.join(pks)})")
    body = ",\n".join(cols_sql)
    return f"CREATE TABLE {table['table']} (\n{body}\n);"


def translate_schema(introspection_json: str, target: str) -> dict:
    """Translate an introspected schema JSON to a target dialect DDL."""
    import json
    try:
        data = json.loads(introspection_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    target = (target or "").lower()
    if target not in {"postgres", "mysql"}:
        return {"status": "error", "error": "target must be 'postgres' or 'mysql'."}
    tables = data.get("tables", [])
    ddl = [_emit_ddl(t, target) for t in tables]
    conversions: List[Dict] = []
    for t in tables:
        for c in t["columns"]:
            mapped = _map_type(c["type"], target)
            if mapped.upper() != c["type"].upper():
                conversions.append({
                    "table": t["table"], "column": c["name"],
                    "from": c["type"], "to": mapped,
                })
    return {
        "status": "ok",
        "target": target,
        "ddl": "\n\n".join(ddl),
        "type_conversions": conversions,
        "conversion_count": len(conversions),
    }


def foreign_key_plan(introspection_json: str, target: str) -> dict:
    """Generate ALTER TABLE statements to re-create foreign keys."""
    import json
    try:
        data = json.loads(introspection_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    target = (target or "").lower()
    if target not in {"postgres", "mysql"}:
        return {"status": "error", "error": "target must be 'postgres' or 'mysql'."}
    statements = []
    for t in data.get("tables", []):
        for fk in t.get("foreign_keys", []):
            if target == "postgres":
                statements.append(
                    f"ALTER TABLE {t['table']} ADD CONSTRAINT "
                    f"fk_{t['table']}_{fk['from']} FOREIGN KEY ({fk['from']}) "
                    f"REFERENCES {fk['to_table']}({fk['to_col']});"
                )
            else:
                statements.append(
                    f"ALTER TABLE {t['table']} ADD FOREIGN KEY ({fk['from']}) "
                    f"REFERENCES {fk['to_table']}({fk['to_col']});"
                )
    return {"status": "ok", "target": target, "statements": statements, "count": len(statements)}


def estimate_complexity(introspection_json: str) -> dict:
    """Rate migration complexity (low / medium / high) for a schema."""
    import json
    try:
        data = json.loads(introspection_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    tables = data.get("tables", [])
    n_tables = len(tables)
    n_fks = sum(len(t.get("foreign_keys", [])) for t in tables)
    n_idx = sum(len(t.get("indexes", [])) for t in tables)
    score = n_tables + n_fks * 2 + n_idx * 0.5
    if score < 10:
        label = "low"
    elif score < 40:
        label = "medium"
    else:
        label = "high"
    return {
        "status": "ok",
        "label": label,
        "score": score,
        "tables": n_tables,
        "foreign_keys": n_fks,
        "indexes": n_idx,
    }


root_agent = Agent(
    name="sql_migrator_agent",
    model="gemini-2.0-flash",
    description=(
        "Introspects a SQLite database, infers an ER model, and "
        "emits a target-dialect (Postgres / MySQL) DDL script with "
        "type conversions and foreign-key plan."
    ),
    instruction="""
    You are a senior DBA who helps migrate SQLite schemas to
    PostgreSQL or MySQL.

    WORKFLOW:
    1. Call `introspect_sqlite` on the user's .db file to get the
       raw schema JSON.
    2. Call `estimate_complexity` to give the user a difficulty
       label up-front.
    3. Call `translate_schema` to produce the target-dialect DDL.
    4. Call `foreign_key_plan` to emit the ALTER TABLE statements.
    5. Present the result in this order:
         a) Complexity label and counts.
         b) Target DDL in a fenced ```sql block.
         c) Type-conversion table (sqlite_type -> target_type).
         d) Foreign-key ALTER statements.
         e) Three concrete pre-migration checks the user should run
            (e.g. "verify no BLOB > 1 GB", "check INTEGER primary
            keys are not used as timestamps").

    RULES:
    - Never invent columns or tables; only use what introspection
       returns.
    - If a SQLite type isn't in the map, fall back to TEXT and warn.
    - Recommend running the migration inside a transaction.
    """,
    tools=[
        introspect_sqlite, translate_schema, foreign_key_plan,
        estimate_complexity,
    ],
)
