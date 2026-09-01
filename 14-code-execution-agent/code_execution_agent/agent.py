"""Code-execution agent.

A pure-Python ADK agent that can evaluate short, sandboxed Python
expressions. The agent exposes a single tool, ``run_python``, that:

* parses the code in a restricted namespace,
* captures anything written to ``stdout``,
* returns the value of the last expression,
* blocks obviously dangerous builtins (``open``, ``exec``, ``eval``,
  ``__import__``, etc.) so the agent can't escape the sandbox easily.

This is a teaching example - the sandbox is intentionally simple and
not a substitute for a hardened environment.
"""

import io
import sys
from contextlib import redirect_stdout
from typing import Dict

from google.adk.agents import Agent

# --- Restricted execution environment ---------------------------------------
# Only safe builtins are exposed. Anything that touches the filesystem,
# network, or process spawn is removed.
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
}

# A small whitelist of importable, pure-Python math/statistics helpers.
_SAFE_MODULES = {
    "math": __import__("math"),
    "statistics": __import__("statistics"),
    "random": __import__("random"),
    "datetime": __import__("datetime"),
    "json": __import__("json"),
    "re": __import__("re"),
}


def _build_globals() -> Dict:
    return {
        "__builtins__": _SAFE_BUILTINS,
        "__name__": "__sandbox__",
        "__doc__": None,
        **_SAFE_MODULES,
    }


# --- Tool exposed to the agent ----------------------------------------------
def run_python(code: str) -> dict:
    """Execute a short Python snippet and return its result.

    Args:
        code: A string containing Python source code. The last
            expression's value (if any) is returned alongside any
            captured stdout.

    Returns:
        A dict with keys ``status``, ``stdout``, ``result`` and
        optionally ``error``.
    """
    if not code or not code.strip():
        return {"status": "error", "error": "No code provided."}

    # Quick safety net: refuse obviously dangerous calls.
    forbidden = ("open(", "subprocess", "os.system", "os.popen", "importlib",
                  "exec(", "eval(", "__import__", "shutil", "socket", "urllib")
    lower = code.lower()
    for token in forbidden:
        if token in lower:
            return {
                "status": "error",
                "error": f"Operation not allowed in the sandbox: '{token}'.",
            }

    sandbox_globals = _build_globals()
    buffer = io.StringIO()

    try:
        with redirect_stdout(buffer):
            compiled = compile(code, "<sandbox>", "exec")
            exec(compiled, sandbox_globals)
            # Try to evaluate the last expression line for a return value.
            lines = [ln for ln in code.splitlines() if ln.strip()]
            if lines:
                try:
                    last_expr = compile(lines[-1], "<sandbox>", "eval")
                    result = eval(last_expr, sandbox_globals)
                except SyntaxError:
                    result = None
            else:
                result = None
    except Exception as exc:  # noqa: BLE001 - we want to surface any error
        return {
            "status": "error",
            "stdout": buffer.getvalue(),
            "error": f"{type(exc).__name__}: {exc}",
        }

    # Make the result JSON-friendly.
    try:
        import json

        json.dumps(result)
        safe_result = result
    except TypeError:
        safe_result = repr(result)

    return {
        "status": "ok",
        "stdout": buffer.getvalue(),
        "result": safe_result,
    }


# --- Agent definition ---------------------------------------------------------
root_agent = Agent(
    name="code_execution_agent",
    model="gemini-2.0-flash",
    description=(
        "Writes and runs short Python snippets inside a restricted "
        "sandbox to answer quantitative and computational questions."
    ),
    instruction="""
    You are a careful Python data-analysis assistant.

    WORKFLOW:
    1. When the user asks a computational question, write a small
       self-contained Python snippet that solves it.
    2. Call the `run_python` tool with that snippet.
    3. Read the returned `stdout` and `result` and explain the answer
       in plain English.
    4. If the tool returns an `error`, debug the code and try again
       (you have up to 3 attempts).

    RULES:
    - The sandbox forbids file I/O, network calls, and shell access.
    - Prefer pure stdlib (math, statistics, json, re, random, datetime).
    - Always show the snippet you ran before explaining the result.
    - Keep code short (<= 20 lines) and well-commented.
    """,
    tools=[run_python],
)
