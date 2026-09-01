"""System Incident Triage Agent.

Reads a chunk of logs, clusters lines by error fingerprint, matches
clusters against a small runbook library, and returns a root-cause
hypothesis with a confidence score.
"""

import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class IncidentReport(BaseModel):
    fingerprint: str
    cluster_count: int
    line_count: int
    top_signature: str
    suspected_cause: str
    confidence: int
    runbook_steps: List[str]
    severity: str
    summary: str


_RUNBOOKS = {
    "database": {
        "cause": "Database connection pool exhaustion or slow query.",
        "steps": [
            "Check active connections on the DB.",
            "Inspect pg_stat_activity / SHOW PROCESSLIST.",
            "Look for long-running transactions > 30s.",
            "Scale pool size or kill the offending transaction.",
            "Add a query timeout if missing.",
        ],
    },
    "memory": {
        "cause": "Process memory leak or OOM.",
        "steps": [
            "Capture heap dump if not already done.",
            "Check RSS / VMSize growth over the last hour.",
            "Look for unbounded caches or growing queues.",
            "Restart the service as a temporary mitigation.",
            "Patch the leak and add a memory alert at 80%.",
        ],
    },
    "auth": {
        "cause": "Auth provider outage or token validation failure.",
        "steps": [
            "Verify the auth provider's status page.",
            "Check token-validation latency in metrics.",
            "Verify clock skew between app and IdP.",
            "Rotate keys if a compromise is suspected.",
            "Fail open only if product policy allows.",
        ],
    },
    "network": {
        "cause": "Network partition or DNS failure.",
        "steps": [
            "Check DNS resolution from the affected host.",
            "Verify TCP connectivity to the upstream service.",
            "Inspect firewall / security-group rules.",
            "Check the cloud provider's network health dashboard.",
            "Failover to a backup region if multi-region.",
        ],
    },
    "deploy": {
        "cause": "Bad recent deploy introduced the regression.",
        "steps": [
            "Compare error rate before/after the deploy timestamp.",
            "Inspect the diff for risky changes (config, schema, deps).",
            "Roll back via the deploy tool.",
            "Capture the diff in the post-mortem.",
        ],
    },
    "unknown": {
        "cause": "No clear signature matched; needs human investigation.",
        "steps": [
            "Snapshot logs and metrics.",
            "Page the on-call engineer.",
            "Open an incident channel and start the timer.",
        ],
    },
}

_PATTERN_RULES = [
    ("database", [
        r"connection (?:refused|reset|timeout)",
        r"(?:too many connections|max connections)",
        r"deadlock detected",
        r"relation .* does not exist",
        r"duplicate key value",
    ]),
    ("memory", [
        r"out of memory",
        r"OOMKilled",
        r"cannot allocate memory",
        r"MemoryError",
        r"heap space",
    ]),
    ("auth", [
        r"invalid (?:token|jwt|signature)",
        r"unauthorized",
        r"401 ",
        r"token expired",
        r"forbidden",
    ]),
    ("network", [
        r"DNS .* timeout",
        r"no route to host",
        r"connection timed out",
        r"tls handshake",
        r"ssl certificate",
    ]),
    ("deploy", [
        r"recent deploy",
        r"version mismatch",
        r"migration failed",
        r"config invalid",
    ]),
]

_FINGERPRINT_RE = re.compile(r"([A-Z][A-Z0-9_]+(?:ERROR|EXCEPTION|FAIL))")


def _line_fingerprint(line: str) -> str:
    m = _FINGERPRINT_RE.search(line)
    if m:
        return m.group(1)
    tokens = re.findall(r"\w+", line)
    return " ".join(tokens[:4]) if tokens else "UNKNOWN"


def parse_logs(text: str) -> dict:
    """Cluster log lines by fingerprint and return the cluster table."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    lines = [l for l in text.splitlines() if l.strip()]
    clusters: Dict[str, List[str]] = defaultdict(list)
    for ln in lines:
        clusters[_line_fingerprint(ln)].append(ln)
    table = sorted(
        ({"fingerprint": k, "count": len(v), "sample": v[0][:200]} for k, v in clusters.items()),
        key=lambda c: c["count"],
        reverse=True,
    )
    return {
        "status": "ok",
        "line_count": len(lines),
        "cluster_count": len(clusters),
        "clusters": table,
    }


def classify_signature(signature: str) -> dict:
    """Map a log signature (text) to a runbook category."""
    if not signature or not signature.strip():
        return {"status": "error", "error": "signature is required."}
    text = signature.lower()
    scores: Dict[str, int] = {cat: 0 for cat in _RUNBOOKS}
    for cat, patterns in _PATTERN_RULES:
        for p in patterns:
            if re.search(p, text):
                scores[cat] += 1
    best = max(scores.items(), key=lambda kv: kv[1])
    category = best[0] if best[1] > 0 else "unknown"
    confidence = min(100, 50 + best[1] * 15) if best[1] > 0 else 30
    return {
        "status": "ok",
        "category": category,
        "scores": scores,
        "confidence": confidence,
    }


def severity_for(category: str, line_count: int) -> str:
    if category == "unknown":
        return "SEV-3"
    if line_count > 200:
        return "SEV-1"
    if line_count > 50:
        return "SEV-2"
    return "SEV-3"


def runbook(category: str) -> dict:
    """Return the runbook for a category."""
    if category not in _RUNBOOKS:
        return {"status": "error", "error": f"unknown category: {category!r}"}
    return {
        "status": "ok",
        "category": category,
        "cause": _RUNBOOKS[category]["cause"],
        "steps": _RUNBOOKS[category]["steps"],
    }


def triage(text: str) -> dict:
    """One-call triage pipeline."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    parsed = parse_logs(text)
    if not parsed.get("clusters"):
        return {"status": "error", "error": "no log lines found."}
    top = parsed["clusters"][0]
    sig = " ".join([top["sample"], top["fingerprint"]])
    cls = classify_signature(sig)
    rb = runbook(cls["category"])
    sev = severity_for(cls["category"], top["count"])
    return {
        "status": "ok",
        "fingerprint": top["fingerprint"],
        "cluster_count": parsed["cluster_count"],
        "line_count": parsed["line_count"],
        "top_signature": top["sample"],
        "suspected_cause": rb.get("cause", ""),
        "confidence": cls.get("confidence", 0),
        "runbook_steps": rb.get("steps", []),
        "severity": sev,
        "summary": (
            f"{sev}: {cls['category']} signature matches "
            f"{top['count']} lines ({top['fingerprint']}). "
            f"Suspected: {rb.get('cause', '')}"
        ),
    }


root_agent = Agent(
    name="system_incident_agent",
    model="gemini-2.0-flash",
    description=(
        "Triages a log dump: clusters lines by fingerprint, "
        "matches against a built-in runbook library, and "
        "returns a root-cause hypothesis with confidence."
    ),
    instruction="""
    You are an SRE on-call assistant.

    WORKFLOW:
    1. Call `parse_logs` to cluster the user's log dump.
    2. For the top cluster by count, call `classify_signature` to
       map it to a runbook category.
    3. Call `runbook` to fetch the matching runbook.
    4. (Or call `triage` for the all-in-one pipeline.)
    5. Present: severity tag, top fingerprint, suspected cause,
       confidence, and the runbook steps as a numbered list.

    RULES:
    - Never claim 100% confidence; cap at the tool's number.
    - If the top cluster is < 5% of total lines, mention the
       second-largest cluster as an alternative hypothesis.
    - Never suggest destructive actions (e.g. `rm -rf`,
       `DROP DATABASE`) without explicit user confirmation.
    - Keep the summary to <= 60 words.
    """,
    tools=[
        parse_logs, classify_signature, runbook, triage,
    ],
    output_schema=IncidentReport,
    output_key="incident",
)
