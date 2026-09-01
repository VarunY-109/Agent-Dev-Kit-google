"""Expense Auditor Agent.

Reads a list of expenses (JSON), applies a configurable company
policy, and returns a per-item decision (approve / reject / review)
plus anomaly flags.
"""

import json
import statistics
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class ExpenseDecision(BaseModel):
    item: Dict
    decision: str
    reasons: List[str]
    flags: List[str]


class AuditReport(BaseModel):
    total_count: int
    approved_count: int
    rejected_count: int
    review_count: int
    total_amount: float
    flagged_total: float
    decisions: List[ExpenseDecision]


def _amount(item: Dict) -> float:
    try:
        return float(item.get("amount", 0))
    except (TypeError, ValueError):
        return 0.0


def parse_csv_like(text: str) -> dict:
    """Best-effort CSV-ish parser for "date,category,amount,description" rows."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            amount = float(parts[2])
        except ValueError:
            continue
        rows.append({
            "date": parts[0],
            "category": parts[1] if len(parts) > 1 else "misc",
            "amount": amount,
            "description": ",".join(parts[3:]) if len(parts) > 3 else "",
        })
    return {"status": "ok", "items": rows, "count": len(rows)}


def policy_check(item: Dict, policy: Dict) -> dict:
    """Apply a policy dict to a single expense item.

    Supported policy keys: max_per_item, max_per_category_per_month,
    blocked_categories, require_receipt_above.
    """
    reasons: List[str] = []
    flags: List[str] = []
    decision = "approve"
    amt = _amount(item)
    cat = (item.get("category") or "").lower()

    cap = policy.get("max_per_item")
    if cap is not None and amt > float(cap):
        decision = "review"
        reasons.append(f"amount {amt} exceeds per-item cap {cap}")

    blocked = [b.lower() for b in policy.get("blocked_categories", [])]
    if cat in blocked:
        decision = "reject"
        reasons.append(f"category {cat!r} is blocked by policy")

    if amt > float(policy.get("require_receipt_above", 0)):
        if not (item.get("receipt_url") or item.get("has_receipt")):
            decision = "review" if decision == "approve" else decision
            reasons.append("missing receipt above threshold")

    if policy.get("weekend_block") and item.get("date"):
        try:
            from datetime import datetime
            d = datetime.strptime(item["date"], "%Y-%m-%d")
            if d.weekday() >= 5:
                flags.append("weekend")
        except ValueError:
            pass

    if not reasons and not flags:
        reasons.append("within policy")
    return {"status": "ok", "decision": decision, "reasons": reasons, "flags": flags}


def detect_anomalies(items_json: str) -> dict:
    """Flag amounts that are > 3 standard deviations from the category mean."""
    try:
        items = json.loads(items_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(items, list) or not items:
        return {"status": "ok", "anomalies": []}
    by_cat: Dict[str, List[float]] = {}
    for it in items:
        by_cat.setdefault((it.get("category") or "misc").lower(), []).append(_amount(it))
    anomalies = []
    for i, it in enumerate(items):
        cat = (it.get("category") or "misc").lower()
        amounts = by_cat[cat]
        if len(amounts) < 3:
            continue
        mean = statistics.fmean(amounts)
        stdev = statistics.pstdev(amounts) or 1.0
        if abs(_amount(it) - mean) > 3 * stdev:
            anomalies.append({
                "index": i,
                "amount": _amount(it),
                "category": cat,
                "mean": round(mean, 2),
                "stdev": round(stdev, 2),
            })
    return {"status": "ok", "anomalies": anomalies, "count": len(anomalies)}


def audit(items_json: str, policy: Dict) -> dict:
    """Audit a JSON list of expense items against a policy dict."""
    try:
        items = json.loads(items_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(items, list):
        return {"status": "error", "error": "expected a JSON list."}

    anoms = detect_anomalies(items_json).get("anomalies", [])
    anom_idx = {a["index"] for a in anoms}
    decisions: List[Dict] = []
    approved = rejected = review = 0
    total = flagged_total = 0.0
    for i, it in enumerate(items):
        pc = policy_check(it, policy)
        d = pc["decision"]
        flags = list(pc["flags"])
        if i in anom_idx:
            flags.append("anomaly")
            if d == "approve":
                d = "review"
        if d == "approve":
            approved += 1
        elif d == "reject":
            rejected += 1
        else:
            review += 1
        amt = _amount(it)
        total += amt
        if d != "approve":
            flagged_total += amt
        decisions.append({
            "item": it, "decision": d,
            "reasons": pc["reasons"], "flags": flags,
        })
    return {
        "status": "ok",
        "total_count": len(items),
        "approved_count": approved,
        "rejected_count": rejected,
        "review_count": review,
        "total_amount": round(total, 2),
        "flagged_total": round(flagged_total, 2),
        "decisions": decisions,
    }


DEFAULT_POLICY = {
    "max_per_item": 500,
    "blocked_categories": ["alcohol", "gambling", "adult"],
    "require_receipt_above": 75,
    "weekend_block": False,
}


root_agent = Agent(
    name="expense_auditor_agent",
    model="gemini-2.0-flash",
    description=(
        "Audits a list of expenses against a company policy, "
        "flags anomalies, and produces approve/reject/review "
        "decisions per item."
    ),
    instruction="""
    You are a finance-ops expense auditor.

    WORKFLOW:
    1. If the user pastes CSV-like text, call `parse_csv_like`
       first.
    2. Use this default policy unless the user overrides:
         max_per_item=500, blocked_categories=[alcohol, gambling, adult],
         require_receipt_above=75, weekend_block=False.
    3. Call `detect_anomalies` on the item list, then `audit` with
       the policy to get a per-item decision list.
    4. Present a summary table:
         total / approved / rejected / review / flagged_total
       and a bullet list of the items that need human review,
       each with the reason and a suggested next action.

    RULES:
    - Never auto-reject an item over the cap - send it to review.
    - Anomalies are flagged but the agent should not auto-reject.
    - When the policy is ambiguous, prefer `review` over `reject`.
    """,
    tools=[
        parse_csv_like, policy_check, detect_anomalies, audit,
    ],
    output_schema=AuditReport,
    output_key="audit",
)
