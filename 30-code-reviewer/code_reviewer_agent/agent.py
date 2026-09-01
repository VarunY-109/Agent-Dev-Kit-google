"""Code Reviewer Agent.

A multi-signal code reviewer that combines AST-based complexity
metrics, a hand-rolled security/style scan, and a cyclomatic-style
"smell" detector. Produces a scored, prioritised review.
"""

import ast
import re
from collections import Counter
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class Issue(BaseModel):
    severity: str
    line: int
    rule: str
    message: str
    suggestion: str


class ReviewReport(BaseModel):
    language: str
    file: str
    loc: int
    function_count: int
    avg_complexity: float
    score: int
    issues: List[Issue]
    summary: str


_LANGS = {"python": "python", "py": "python",
          "javascript": "javascript", "js": "javascript",
          "typescript": "typescript", "ts": "typescript",
          "go": "go"}


_SECRETS_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]"
)
_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")


def detect_language(path: str) -> dict:
    """Guess the language of a file from its extension."""
    if not path or "." not in path:
        return {"status": "error", "error": "path must include an extension."}
    ext = path.rsplit(".", 1)[-1].lower()
    lang = _LANGS.get(ext)
    if not lang:
        return {"status": "error", "error": f"unsupported extension: {ext!r}"}
    return {"status": "ok", "language": lang, "extension": ext}


def complexity_metrics(source: str) -> dict:
    """Return per-function cyclomatic complexity for a Python source."""
    if not source or not source.strip():
        return {"status": "error", "error": "source is required."}
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"status": "error", "error": f"parse error: {exc}"}
    funcs: List[Dict] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef):
            complexity = 1
            for n in ast.walk(node):
                if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                  ast.With, ast.Assert, ast.BoolOp, ast.IfExp,
                                  ast.Match)):
                    complexity += 1
                if isinstance(n, ast.BoolOp):
                    complexity += max(0, len(n.values) - 1)
            funcs.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": complexity,
                "args": len(node.args.args),
                "loc": (node.end_lineno or node.lineno) - node.lineno + 1,
            })
            self.generic_visit(node)

    Visitor().visit(tree)
    avg = round(sum(f["complexity"] for f in funcs) / max(1, len(funcs)), 2)
    return {
        "status": "ok",
        "function_count": len(funcs),
        "avg_complexity": avg,
        "max_complexity": max((f["complexity"] for f in funcs), default=0),
        "functions": funcs,
    }


def security_scan(source: str) -> dict:
    """Look for hard-coded secrets, `eval`/`exec` and shell=True."""
    if not source or not source.strip():
        return {"status": "error", "error": "source is required."}
    findings: List[Dict] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if _SECRETS_RE.search(line):
            findings.append({"line": i, "rule": "SECRET", "match": line.strip()[:120]})
        if re.search(r"\b(eval|exec)\s*\(", line):
            findings.append({"line": i, "rule": "DANGEROUS_BUILTIN", "match": line.strip()[:120]})
        if re.search(r"shell\s*=\s*True", line):
            findings.append({"line": i, "rule": "SHELL_INJECTION", "match": line.strip()[:120]})
        if re.search(r"subprocess\.(call|run|Popen).*shell\s*=\s*True", line):
            findings.append({"line": i, "rule": "SHELL_INJECTION", "match": line.strip()[:120]})
    return {"status": "ok", "finding_count": len(findings), "findings": findings}


def style_smells(source: str) -> dict:
    """Detect long lines, missing docstrings on defs/classes, and TODOs."""
    if not source or not source.strip():
        return {"status": "error", "error": "source is required."}
    smells: List[Dict] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if len(line) > 100:
            smells.append({"line": i, "rule": "LONG_LINE", "length": len(line)})
        if _TODO_RE.search(line):
            smells.append({"line": i, "rule": "TODO", "match": line.strip()[:120]})
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"status": "ok", "smell_count": len(smells), "smells": smells}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Str, ast.Constant))
                    and isinstance(getattr(node.body[0].value, "s", None) or node.body[0].value.value, str)):
                smells.append({
                    "line": node.lineno,
                    "rule": "MISSING_DOCSTRING",
                    "match": node.name,
                })
    return {"status": "ok", "smell_count": len(smells), "smells": smells}


def duplication_score(source: str) -> dict:
    """Estimate the duplicated-line ratio using 6-line windows."""
    if not source or not source.strip():
        return {"status": "error", "error": "source is required."}
    lines = [ln.strip() for ln in source.splitlines() if ln.strip()]
    if len(lines) < 6:
        return {"status": "ok", "duplicate_ratio": 0.0, "duplicate_lines": 0}
    seen: Counter = Counter()
    dup = 0
    for i in range(len(lines) - 5):
        key = tuple(lines[i:i + 6])
        if key in seen:
            dup += 6
        seen[key] += 1
    ratio = round(dup / max(1, len(lines)), 3)
    return {"status": "ok", "duplicate_ratio": ratio, "duplicate_lines": dup}


def score_review(metrics_json: str, security_json: str,
                 smells_json: str) -> dict:
    """Aggregate the three scans into a 0-100 score."""
    try:
        m = json.loads(metrics_json)
        s = json.loads(security_json)
        sm = json.loads(smells_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    score = 100
    score -= min(40, m.get("max_complexity", 0) * 2)
    score -= min(30, s.get("finding_count", 0) * 10)
    score -= min(20, sm.get("smell_count", 0))
    score = max(0, score)
    return {"status": "ok", "score": score}


import json as _json


def review(source: str, path: str = "snippet.py") -> dict:
    """Run all scans and return a combined review dict."""
    if not source or not source.strip():
        return {"status": "error", "error": "source is required."}
    lang = detect_language(path)
    m = complexity_metrics(source)
    sec = security_scan(source)
    sm = style_smells(source)
    dup = duplication_score(source)
    metrics = m if m["status"] == "ok" else {"max_complexity": 0, "function_count": 0, "avg_complexity": 0}
    score_res = score_review(_json.dumps(metrics), _json.dumps(sec), _json.dumps(sm))
    issues: List[Dict] = []
    for f in sec.get("findings", []):
        issues.append({
            "severity": "high", "line": f["line"], "rule": f["rule"],
            "message": f["match"], "suggestion": "Move secret to env / vault.",
        })
    for s in sm.get("smells", []):
        sev = "low"
        sugg = "Refactor."
        if s["rule"] == "LONG_LINE":
            sugg = "Wrap or break the line (<= 100 chars)."
        if s["rule"] == "TODO":
            sugg = "Resolve or convert to a tracked issue."
        if s["rule"] == "MISSING_DOCSTRING":
            sugg = "Add a one-line docstring."
        issues.append({
            "severity": sev, "line": s["line"], "rule": s["rule"],
            "message": str(s.get("match", s.get("length", ""))),
            "suggestion": sugg,
        })
    return {
        "status": "ok",
        "language": lang.get("language", "unknown"),
        "file": path,
        "loc": len(source.splitlines()),
        "function_count": metrics.get("function_count", 0),
        "avg_complexity": metrics.get("avg_complexity", 0.0),
        "score": score_res.get("score", 0),
        "issues": issues,
        "duplication": dup.get("duplicate_ratio", 0.0),
    }


root_agent = Agent(
    name="code_reviewer_agent",
    model="gemini-2.0-flash",
    description=(
        "Reviews a code snippet with complexity, security, style, "
        "and duplication scans, returning a scored, prioritised list "
        "of issues with line numbers and fix suggestions."
    ),
    instruction="""
    You are a senior software engineer performing a code review.

    WORKFLOW for every snippet:
    1. Call `detect_language` to confirm the language.
    2. Call `complexity_metrics` (Python) or skip for other langs.
    3. Call `security_scan`, `style_smells`, `duplication_score`.
    4. Call `score_review` to compute the overall score.
    5. Call `review` to assemble a final, sorted, de-duplicated
       issue list.

    DELIVERABLES:
    - Score (0-100) and one-line interpretation.
    - Bullet list of HIGH-severity issues first, then MEDIUM, then
       LOW, each with: file, line, rule, message, suggested fix.
    - Two high-impact refactor suggestions grounded in the metrics
       (e.g. "Function X has complexity 14 - extract a helper").

    RULES:
    - Never invent issues that the tools didn't surface.
    - For non-Python code, skip complexity_metrics but still run
       security_scan, style_smells (best-effort) and duplication_score.
    - Be specific in suggestions; no generic "improve readability".
    """,
    tools=[
        detect_language, complexity_metrics, security_scan,
        style_smells, duplication_score, score_review, review,
    ],
    output_schema=ReviewReport,
    output_key="review",
)
