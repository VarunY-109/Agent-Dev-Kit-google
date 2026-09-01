"""Calculator Agent.

A pure-Python ADK agent that evaluates arithmetic expressions
**deterministically** using Python's own ``ast`` parser. Because the
LLM can still make arithmetic mistakes, this pattern keeps the math
itself exact while letting the model handle natural-language prompts
("What is 12% tip on a $84.50 bill?").

Tools:
    * ``calculate``  - evaluate a Python arithmetic expression.
    * ``unit_convert`` - convert between common units (length, mass,
                         temperature, data).
    * ``percentage`` - compute percentage, percent change, and
                       percent-of totals.
"""

import ast
import math
import operator
import re
from typing import Dict

from google.adk.agents import Agent

# Whitelist of binary operators allowed in `calculate`.
_BIN_OPS: Dict[type, object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: Dict[type, object] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": math.nan,
}
_FUNCTIONS = {
    name: getattr(math, name)
    for name in (
        "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh", "log", "log2", "log10", "log1p",
        "exp", "expm1", "sqrt", "cbrt", "pow", "ceil", "floor",
        "fabs", "factorial", "gcd", "lcm", "degrees", "radians",
        "isnan", "isinf", "isfinite", "trunc",
    )
    if hasattr(math, name)
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise ValueError(f"Operator not allowed: {op_type.__name__}")
        return _BIN_OPS[op_type](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"Unary operator not allowed: {op_type.__name__}")
        return _UNARY_OPS[op_type](_safe_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise ValueError(f"Unknown name: {node.id!r}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ValueError("Only whitelisted math functions are allowed.")
        if node.keywords:
            raise ValueError("Keyword arguments are not supported.")
        args = [_safe_eval(arg) for arg in node.args]
        return _FUNCTIONS[node.func.id](*args)
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


# --- Tools -------------------------------------------------------------------
def calculate(expression: str) -> dict:
    """Evaluate an arithmetic expression and return the exact result.

    Args:
        expression: A Python arithmetic expression, e.g.
            ``"2 * (3 + 4) ** 2"`` or ``"sin(pi / 4)"``.

    Returns:
        A dict with ``status`` and ``result`` (a float) or ``error``.
    """
    if not expression or not expression.strip():
        return {"status": "error", "error": "Expression cannot be empty."}
    try:
        tree = ast.parse(expression, mode="eval")
        value = _safe_eval(tree)
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    if isinstance(value, float):
        if math.isnan(value):
            pretty = "NaN"
        elif math.isinf(value):
            pretty = "Infinity" if value > 0 else "-Infinity"
        else:
            pretty = f"{value:.10g}"
    else:
        pretty = str(value)
    return {"status": "ok", "expression": expression, "result": value, "pretty": pretty}


# --- Unit conversion tables --------------------------------------------------
_LENGTH_TO_M = {
    "mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
    "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
}
_MASS_TO_KG = {
    "mg": 1e-6, "g": 1e-3, "kg": 1.0, "t": 1000.0,
    "oz": 0.0283495, "lb": 0.453592,
}
_DATA_TO_BYTES = {
    "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4,
    "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3, "TiB": 1024 ** 4,
}

_TEMP_UNITS = {"C", "F", "K"}


def _convert_temperature(value: float, src: str, dst: str) -> float:
    # Convert to Celsius first.
    if src == "C":
        c = value
    elif src == "F":
        c = (value - 32) * 5 / 9
    elif src == "K":
        c = value - 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {src!r}")
    if dst == "C":
        return c
    if dst == "F":
        return c * 9 / 5 + 32
    if dst == "K":
        return c + 273.15
    raise ValueError(f"Unknown temperature unit: {dst!r}")


def unit_convert(value: float, src_unit: str, dst_unit: str, kind: str = "") -> dict:
    """Convert a value between two units of the same kind.

    Args:
        value:    The numeric value to convert.
        src_unit: Source unit symbol (e.g. ``"km"``).
        dst_unit: Destination unit symbol (e.g. ``"mi"``).
        kind:     ``"length"``, ``"mass"``, ``"data"`` or ``"temp"``.
                  If empty, it is auto-detected.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return {"status": "error", "error": "value must be a number."}
    src, dst = src_unit.strip(), dst_unit.strip()
    if not src or not dst:
        return {"status": "error", "error": "Both src_unit and dst_unit are required."}

    # Auto-detect the kind if not provided.
    if not kind:
        if src in _LENGTH_TO_M and dst in _LENGTH_TO_M:
            kind = "length"
        elif src in _MASS_TO_KG and dst in _MASS_TO_KG:
            kind = "mass"
        elif src in _DATA_TO_BYTES and dst in _DATA_TO_BYTES:
            kind = "data"
        elif src in _TEMP_UNITS and dst in _TEMP_UNITS:
            kind = "temp"
        else:
            return {
                "status": "error",
                "error": (
                    f"Cannot auto-detect kind for '{src}' -> '{dst}'. "
                    "Pass kind= explicitly (length/mass/data/temp)."
                ),
            }

    try:
        if kind == "length":
            result = v * _LENGTH_TO_M[src] / _LENGTH_TO_M[dst]
        elif kind == "mass":
            result = v * _MASS_TO_KG[src] / _MASS_TO_KG[dst]
        elif kind == "data":
            result = v * _DATA_TO_BYTES[src] / _DATA_TO_BYTES[dst]
        elif kind == "temp":
            result = _convert_temperature(v, src, dst)
        else:
            return {"status": "error", "error": f"Unknown kind: {kind!r}"}
    except KeyError as exc:
        return {"status": "error", "error": f"Unsupported unit: {exc.args[0]!r}"}

    return {
        "status": "ok",
        "value": v,
        "from": f"{v} {src}",
        "to": f"{result:.6g} {dst}",
        "result": result,
    }


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def percentage(part: float, whole: float, mode: str = "of") -> dict:
    """Perform common percentage calculations.

    Args:
        part:  The numerator (or new value for percent change).
        whole: The denominator (or old value for percent change).
        mode:  ``"of"`` (what is part/whole * 100),
               ``"is"`` (whole * part/100),
               ``"change"`` ((part-whole)/whole * 100).
    """
    try:
        p, w = float(part), float(whole)
    except (TypeError, ValueError):
        return {"status": "error", "error": "part and whole must be numbers."}
    if mode == "of":
        if w == 0:
            return {"status": "error", "error": "whole cannot be zero."}
        result = p / w * 100
        pretty = f"{p} is {result:.4g}% of {w}"
    elif mode == "is":
        result = w * p / 100
        pretty = f"{p}% of {w} is {result:.6g}"
    elif mode == "change":
        if w == 0:
            return {"status": "error", "error": "old value cannot be zero."}
        result = (p - w) / w * 100
        pretty = f"Change from {w} to {p} is {result:+.4g}%"
    else:
        return {"status": "error", "error": f"Unknown mode: {mode!r}"}
    return {"status": "ok", "mode": mode, "result": result, "pretty": pretty}


# --- Agent definition ---------------------------------------------------------
root_agent = Agent(
    name="calculator_agent",
    model="gemini-2.0-flash",
    description=(
        "Performs exact arithmetic, unit conversions and percentage "
        "calculations using Python's `ast` parser."
    ),
    instruction="""
    You are a precise calculator assistant. NEVER do arithmetic in
    your head - always delegate to the tools.

    WORKFLOW:
    1. For pure math, write a Python expression and call `calculate`.
    2. For "what is X% of Y" / "X is what % of Y" / "percent change",
       use `percentage` with the right `mode`.
    3. For "convert 5 km to miles", use `unit_convert` (the kind is
       auto-detected when possible).
    4. If a user request mixes multiple steps, chain the tools and
       present each intermediate result.

    RULES:
    - Round to a reasonable number of significant digits in prose.
    - Show the original expression or value alongside the answer.
    - If the tool returns an error, surface the error verbatim.
    """,
    tools=[calculate, unit_convert, percentage],
)
