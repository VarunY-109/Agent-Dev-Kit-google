"""CSV Data Analyst Agent.

A pure-Python ADK agent that loads a local CSV file into memory and
exposes simple analytical tools built on Python's stdlib ``csv``
module. The agent then uses the LLM to interpret the results in
natural language.

Tools:
    * ``load_csv``           - read a CSV file, infer dtypes, cache
                               the dataset in memory.
    * ``preview``            - return the first N rows as JSON.
    * ``column_stats``       - count / mean / min / max for numeric
                               columns; value counts for strings.
    * ``filter_rows``        - filter by an arbitrary equality
                               condition (``column == value``).
    * ``group_by``           - group by a column and aggregate a
                               second column with sum/mean/count.
"""

import csv
import os
import statistics
from typing import Any, Dict, List, Optional

from google.adk.agents import Agent

# Per-process in-memory cache: path -> {"rows": [...], "columns": [...], "dtypes": {...}}
_CACHE: Dict[str, Dict[str, Any]] = {}

_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
_MAX_ROWS = 200_000


def _infer_dtype(values: List[str]) -> str:
    """Best-effort dtype inference: 'int', 'float' or 'string'."""
    sample = [v for v in values if v not in ("", None)][:200]
    if not sample:
        return "string"
    try:
        for v in sample:
            int(v)
        return "int"
    except ValueError:
        pass
    try:
        for v in sample:
            float(v)
        return "float"
    except ValueError:
        pass
    return "string"


def _to_number(v: str) -> Any:
    """Try to convert a string to int/float; otherwise return as-is."""
    if v == "" or v is None:
        return None
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _read_csv(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
    columns = list(rows[0].keys()) if rows else []
    dtypes: Dict[str, str] = {}
    for col in columns:
        dtypes[col] = _infer_dtype([str(r.get(col, "")) for r in rows])
    return {"rows": rows, "columns": columns, "dtypes": dtypes}


# --- Tools -------------------------------------------------------------------
def load_csv(path: str) -> dict:
    """Load a CSV file into the agent's in-memory cache.

    Args:
        path: Filesystem path to a UTF-8 CSV file.
    """
    if not path:
        return {"status": "error", "error": "path is required."}
    if not os.path.isfile(path):
        return {"status": "error", "error": f"File not found: {path!r}"}
    size = os.path.getsize(path)
    if size > _MAX_BYTES:
        return {"status": "error", "error": f"CSV is {size} bytes; max is {_MAX_BYTES}."}

    try:
        data = _read_csv(path)
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        return {"status": "error", "error": f"Failed to read CSV: {exc}"}

    if len(data["rows"]) > _MAX_ROWS:
        return {
            "status": "error",
            "error": f"CSV has {len(data['rows'])} rows; max is {_MAX_ROWS}.",
        }

    _CACHE[path] = data
    return {
        "status": "ok",
        "path": os.path.abspath(path),
        "row_count": len(data["rows"]),
        "columns": data["columns"],
        "dtypes": data["dtypes"],
    }


def preview(path: str, n: int = 5) -> dict:
    """Return the first ``n`` rows of the cached CSV."""
    data = _CACHE.get(path)
    if not data:
        return {"status": "error", "error": "CSV not loaded - call load_csv first."}
    n = max(1, min(int(n), 100))
    return {
        "status": "ok",
        "row_count": len(data["rows"]),
        "preview": data["rows"][:n],
    }


def column_stats(path: str, column: str) -> dict:
    """Compute summary statistics for a single column."""
    data = _CACHE.get(path)
    if not data:
        return {"status": "error", "error": "CSV not loaded - call load_csv first."}
    if column not in data["columns"]:
        return {"status": "error", "error": f"Unknown column: {column!r}"}

    values = [r.get(column, "") for r in data["rows"]]
    dtype = data["dtypes"].get(column, "string")
    missing = sum(1 for v in values if v in ("", None))

    stats: Dict[str, Any] = {
        "column": column,
        "dtype": dtype,
        "count": len(values),
        "missing": missing,
    }

    if dtype in {"int", "float"}:
        nums = [v for v in (_to_number(v) for v in values) if isinstance(v, (int, float))]
        if nums:
            stats.update({
                "min": min(nums),
                "max": max(nums),
                "mean": round(statistics.fmean(nums), 6),
                "median": statistics.median(nums),
                "stdev": round(statistics.pstdev(nums), 6) if len(nums) > 1 else 0.0,
            })
    else:
        from collections import Counter
        top = Counter(values).most_common(5)
        stats["top_values"] = [{"value": v, "count": c} for v, c in top]
        stats["unique"] = len(set(values))

    return {"status": "ok", "stats": stats}


def filter_rows(path: str, column: str, value: str, limit: int = 50) -> dict:
    """Return rows where ``column == value`` (string comparison)."""
    data = _CACHE.get(path)
    if not data:
        return {"status": "error", "error": "CSV not loaded - call load_csv first."}
    if column not in data["columns"]:
        return {"status": "error", "error": f"Unknown column: {column!r}"}
    matches = [r for r in data["rows"] if str(r.get(column, "")) == str(value)]
    return {
        "status": "ok",
        "matched": len(matches),
        "rows": matches[: max(1, min(int(limit), 500))],
    }


def group_by(path: str, group_column: str, target_column: str,
             agg: str = "sum") -> dict:
    """Group by ``group_column`` and aggregate ``target_column``."""
    data = _CACHE.get(path)
    if not data:
        return {"status": "error", "error": "CSV not loaded - call load_csv first."}
    for col in (group_column, target_column):
        if col not in data["columns"]:
            return {"status": "error", "error": f"Unknown column: {col!r}"}

    if agg not in {"sum", "mean", "count", "min", "max"}:
        return {"status": "error", "error": f"Unsupported aggregation: {agg!r}"}

    groups: Dict[str, List[Any]] = {}
    for r in data["rows"]:
        key = r.get(group_column, "")
        groups.setdefault(key, []).append(r.get(target_column, ""))

    results = []
    for key, vals in groups.items():
        if agg == "count":
            value: Optional[float] = len(vals)
        else:
            nums = [v for v in (_to_number(v) for v in vals)
                    if isinstance(v, (int, float))]
            if not nums and agg != "count":
                value = None
            elif agg == "sum":
                value = sum(nums)
            elif agg == "mean":
                value = round(statistics.fmean(nums), 6)
            elif agg == "min":
                value = min(nums)
            else:  # max
                value = max(nums)
        results.append({"key": key, agg: value})

    # Sort descending for sum/mean/count, ascending for min/max.
    reverse = agg in {"sum", "mean", "count"}
    results.sort(key=lambda r: (r[agg] is None, -(r[agg] or 0) if reverse else (r[agg] or 0)))
    return {"status": "ok", "groups": results}


# --- Agent definition ---------------------------------------------------------
root_agent = Agent(
    name="csv_data_analyst_agent",
    model="gemini-2.0-flash",
    description=(
        "Loads a local CSV file and answers analytical questions "
        "about it using pure-Python statistics."
    ),
    instruction="""
    You are a data analyst that answers questions about CSV files.

    WORKFLOW:
    1. When the user provides a path, call `load_csv` first to
       ingest the file. Note the columns and inferred dtypes.
    2. Use `column_stats` to explore individual columns, `preview`
       to see sample rows, `filter_rows` for equality lookups and
       `group_by` for aggregations.
    3. Synthesise the answer in plain English and present key
       numbers as a small table.

    RULES:
    - Never invent numbers. Only report what the tools return.
    - For aggregations other than count, the target column must be
       numeric; the tool will return null otherwise - call out the
       limitation honestly.
    - Keep responses under 200 words unless the user asks for
       detail; show the numbers, not long prose.
    """,
    tools=[load_csv, preview, column_stats, filter_rows, group_by],
)
