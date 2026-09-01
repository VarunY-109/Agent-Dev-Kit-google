"""Investment Allocator Agent.

A Markowitz-lite portfolio rebalancer. Takes the current holdings
and a target risk profile, then recommends trades to move toward
the target weights.
"""

import json
import math
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class Trade(BaseModel):
    ticker: str
    action: str
    shares: int
    estimated_value_usd: float


class RebalancePlan(BaseModel):
    target_profile: str
    current_value_usd: float
    target_value_usd: float
    trades: List[Trade]
    expected_volatility_pct: float
    notes: str


_PROFILE_TARGETS = {
    "conservative": {"bonds": 0.7, "stocks": 0.25, "cash": 0.05,
                     "vol": 6.0},
    "balanced":     {"bonds": 0.4, "stocks": 0.55, "cash": 0.05,
                     "vol": 10.0},
    "aggressive":   {"bonds": 0.1, "stocks": 0.85, "cash": 0.05,
                     "vol": 16.0},
    "all_weather":  {"bonds": 0.55, "stocks": 0.30, "gold": 0.10,
                     "cash": 0.05, "vol": 7.5},
}


def profile_targets(profile: str) -> dict:
    """Return the canonical weight template for a named profile."""
    p = (profile or "").lower().replace(" ", "_").replace("-", "_")
    if p not in _PROFILE_TARGETS:
        return {
            "status": "error",
            "error": f"profile must be one of: {list(_PROFILE_TARGETS)}",
        }
    return {"status": "ok", "profile": p, **_PROFILE_TARGETS[p]}


_ASSET_CLASS_OF_TICKER = {
    "AGG": "bonds", "BND": "bonds", "TLT": "bonds",
    "VTI": "stocks", "VOO": "stocks", "SPY": "stocks", "QQQ": "stocks",
    "GLD": "gold", "IAU": "gold",
}


def classify_holding(ticker: str) -> dict:
    """Classify a ticker into an asset class using a small built-in map."""
    t = (ticker or "").upper()
    if t in _ASSET_CLASS_OF_TICKER:
        return {"status": "ok", "ticker": t, "asset_class": _ASSET_CLASS_OF_TICKER[t]}
    return {"status": "ok", "ticker": t, "asset_class": "stocks"}


def portfolio_value(holdings_json: str) -> dict:
    """Compute the total value of a portfolio.

    Input JSON list of ``{"ticker": str, "shares": int, "price": float}``.
    """
    try:
        holdings = json.loads(holdings_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    total = sum(float(h.get("shares", 0)) * float(h.get("price", 0))
                for h in holdings)
    by_class: Dict[str, float] = {}
    for h in holdings:
        ac = _ASSET_CLASS_OF_TICKER.get(h.get("ticker", "").upper(), "stocks")
        by_class[ac] = by_class.get(ac, 0) + float(h["shares"]) * float(h["price"])
    return {
        "status": "ok",
        "total_value_usd": round(total, 2),
        "by_asset_class_usd": {k: round(v, 2) for k, v in by_class.items()},
    }


def drift(holdings_json: str, target_profile: str) -> dict:
    """Return the weight drift per asset class vs the target profile."""
    p = profile_targets(target_profile)
    if p["status"] != "ok":
        return p
    pv = portfolio_value(holdings_json)
    if pv["status"] != "ok":
        return pv
    total = pv["total_value_usd"]
    current = {k: v / total for k, v in pv["by_asset_class_usd"].items()} if total else {}
    drift_map = {}
    for asset, weight in p.items():
        if asset in {"status", "profile", "vol"}:
            continue
        drift_map[asset] = round(weight - current.get(asset, 0.0), 4)
    return {
        "status": "ok",
        "profile": p["profile"],
        "current_weights": {k: round(v, 4) for k, v in current.items()},
        "drift": drift_map,
        "total_value_usd": total,
    }


def rebalance_plan(holdings_json: str, target_profile: str,
                   new_capital_usd: float = 0.0) -> dict:
    """Generate a list of buy/sell trades to reach the target profile.

    The plan is greedy: per asset class with positive drift, buy
    enough of the first ticker in the class; per class with negative
    drift, sell from the largest holding.
    """
    p = profile_targets(target_profile)
    if p["status"] != "ok":
        return p
    try:
        holdings = json.loads(holdings_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}

    pv = portfolio_value(holdings_json)
    total = pv["total_value_usd"] + float(new_capital_usd)
    trades: List[Dict] = []
    for asset, target_w in p.items():
        if asset in {"status", "profile", "vol"}:
            continue
        target_value = total * target_w
        current_value = pv["by_asset_class_usd"].get(asset, 0.0)
        delta = target_value - current_value
        if abs(delta) < 1:
            continue
        candidates = [h for h in holdings
                      if _ASSET_CLASS_OF_TICKER.get(h["ticker"].upper()) == asset]
        if not candidates:
            continue
        if delta > 0:
            t = candidates[0]
            price = float(t["price"])
            if price <= 0:
                continue
            shares = max(1, int(delta / price))
            trades.append({
                "ticker": t["ticker"],
                "action": "buy",
                "shares": shares,
                "estimated_value_usd": round(shares * price, 2),
            })
        else:
            t = max(candidates, key=lambda h: float(h["shares"]) * float(h["price"]))
            price = float(t["price"])
            if price <= 0:
                continue
            shares = min(int(t["shares"]), max(1, int(-delta / price)))
            trades.append({
                "ticker": t["ticker"],
                "action": "sell",
                "shares": shares,
                "estimated_value_usd": round(shares * price, 2),
            })
    return {
        "status": "ok",
        "profile": p["profile"],
        "current_value_usd": pv["total_value_usd"],
        "target_value_usd": round(total, 2),
        "trades": trades,
        "expected_volatility_pct": p["vol"],
        "notes": "Trades are an approximation; review for tax + fee impact.",
    }


def risk_score(holdings_json: str) -> dict:
    """Compute a 0-100 risk score (higher = riskier)."""
    pv = portfolio_value(holdings_json)
    if pv["status"] != "ok":
        return pv
    total = pv["total_value_usd"] or 1.0
    weights = {k: v / total for k, v in pv["by_asset_class_usd"].items()}
    risk_w = {"stocks": 1.0, "gold": 0.5, "bonds": 0.2, "cash": 0.0}
    score = sum(weights.get(k, 0) * w for k, w in risk_w.items()) * 100
    label = "high" if score >= 70 else "medium" if score >= 35 else "low"
    return {
        "status": "ok",
        "score": round(score, 1),
        "label": label,
        "weights": {k: round(v, 3) for k, v in weights.items()},
    }


root_agent = Agent(
    name="investment_allocator_agent",
    model="gemini-2.0-flash",
    description=(
        "Suggests buy/sell trades to rebalance a portfolio toward "
        "a target risk profile, with a 0-100 risk score."
    ),
    instruction="""
    You are a disciplined, conservative portfolio rebalancer.

    WORKFLOW:
    1. Call `portfolio_value` to size the book and split by class.
    2. Call `risk_score` to give the user a 0-100 risk label.
    3. Call `drift` against the chosen profile to see where the
       portfolio is over/under-weight.
    4. Call `rebalance_plan` to produce a concrete trade list.
    5. Present: current weights, target weights, drift, trades,
       and an expected volatility figure.

    RULES:
    - Never recommend a profile more aggressive than the user
       requested. If they say "balanced" and the portfolio is
       already aggressive, recommend trimming stocks, not adding.
    - Disclose that this is educational, not financial advice.
    - When the drift is small (< 2% per class), say "rebalance is
       optional; consider tax drag" instead of producing trades.
    """,
    tools=[
        profile_targets, classify_holding, portfolio_value, drift,
        rebalance_plan, risk_score,
    ],
    output_schema=RebalancePlan,
    output_key="rebalance",
)
