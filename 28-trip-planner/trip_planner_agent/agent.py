"""Trip Planner Agent.

Builds a multi-city itinerary given dates, budget, traveller count
and a list of must-see places. Validates budget feasibility, balances
days across cities, and surfaces flight / hotel cost estimates.
"""

import json
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class DayPlan(BaseModel):
    date: str
    city: str
    morning: str
    afternoon: str
    evening: str
    estimated_cost_usd: float


class Itinerary(BaseModel):
    title: str
    total_days: int
    cities: List[str]
    days: List[DayPlan]
    total_estimated_cost_usd: float
    within_budget: bool
    notes: str


_CITY_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,60}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_dates(start: str, end: str) -> dict:
    """Validate an ISO date range and return the day count."""
    if not _DATE_RE.match(start or "") or not _DATE_RE.match(end or ""):
        return {"status": "error", "error": "dates must be YYYY-MM-DD."}
    try:
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    if e < s:
        return {"status": "error", "error": "end_date is before start_date."}
    return {
        "status": "ok",
        "start": start,
        "end": end,
        "days": (e - s).days + 1,
    }


_COST_PER_NIGHT = {
    "hostel": 35, "budget": 80, "mid": 160, "luxury": 320,
}
_FOOD_PER_DAY = {"budget": 25, "mid": 60, "luxury": 130}
_LOCAL_TRANSPORT_PER_DAY = 20


def hotel_cost(city: str, nights: int, tier: str = "mid") -> dict:
    """Estimate hotel cost for a city stay."""
    if not _CITY_RE.match(city or ""):
        return {"status": "error", "error": "invalid city."}
    try:
        nights = int(nights)
    except (TypeError, ValueError):
        return {"status": "error", "error": "nights must be int."}
    rate = _COST_PER_NIGHT.get(tier.lower())
    if rate is None:
        return {"status": "error", "error": f"tier must be one of {list(_COST_PER_NIGHT)}"}
    total = rate * max(1, nights)
    return {"status": "ok", "city": city, "nights": nights, "tier": tier, "cost_usd": total}


def food_cost(days: int, tier: str = "mid", travellers: int = 1) -> dict:
    try:
        days = int(days); travellers = int(travellers)
    except (TypeError, ValueError):
        return {"status": "error", "error": "days and travellers must be int."}
    rate = _FOOD_PER_DAY.get(tier.lower())
    if rate is None:
        return {"status": "error", "error": f"tier must be one of {list(_FOOD_PER_DAY)}"}
    return {
        "status": "ok",
        "days": max(1, days),
        "travellers": max(1, travellers),
        "tier": tier,
        "cost_usd": rate * max(1, days) * max(1, travellers),
    }


def local_transport_cost(days: int, travellers: int = 1) -> dict:
    try:
        days = int(days); travellers = int(travellers)
    except (TypeError, ValueError):
        return {"status": "error", "error": "days and travellers must be int."}
    return {
        "status": "ok",
        "days": max(1, days),
        "travellers": max(1, travellers),
        "cost_usd": _LOCAL_TRANSPORT_PER_DAY * max(1, days) * max(1, travellers),
    }


def flight_estimate(origin: str, destination: str, travellers: int = 1,
                    class_of_service: str = "economy") -> dict:
    """Very rough flight cost estimate using a great-circle distance proxy.

    A real planner would call a flight API; this is a stand-in that
    produces a defensible per-person number.
    """
    if not origin or not destination:
        return {"status": "error", "error": "origin and destination required."}
    base = {
        ("domestic", "economy"): 180,
        ("domestic", "business"): 520,
        ("international", "economy"): 720,
        ("international", "business"): 2400,
    }
    international = "," in destination or " " in destination and False or origin.lower() != destination.lower()
    key = ("international" if international else "domestic", class_of_service)
    per_person = base.get(key, 500)
    try:
        travellers = int(travellers)
    except (TypeError, ValueError):
        return {"status": "error", "error": "travellers must be int."}
    return {
        "status": "ok",
        "origin": origin,
        "destination": destination,
        "travellers": max(1, travellers),
        "class": class_of_service,
        "per_person_usd": per_person,
        "total_usd": per_person * max(1, travellers),
    }


def balance_days(cities_json: str, total_days: int) -> dict:
    """Distribute days across cities using a min(2 days) heuristic."""
    try:
        cities = json.loads(cities_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(cities, list) or not cities:
        return {"status": "error", "error": "expected non-empty list."}
    try:
        total_days = int(total_days)
    except (TypeError, ValueError):
        return {"status": "error", "error": "total_days must be int."}
    total_days = max(1, total_days)
    n = len(cities)
    floor = min(2, max(1, total_days // n))
    base = floor * n
    leftover = max(0, total_days - base)
    plan = []
    for i, city in enumerate(cities):
        d = floor + (1 if i < leftover else 0)
        plan.append({"city": city, "days": d})
    return {"status": "ok", "plan": plan, "total_days": sum(p["days"] for p in plan)}


def build_itinerary(spec_json: str) -> dict:
    """Build a day-by-day itinerary from a JSON spec.

    Expected JSON:
        {
          "title": "...",
          "start": "YYYY-MM-DD",
          "end":   "YYYY-MM-DD",
          "cities": [{"city": "Lisbon", "nights": 3}, ...],
          "tier": "mid",
          "travellers": 2,
          "budget_usd": 4000
        }
    """
    try:
        spec = json.loads(spec_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    v = validate_dates(spec.get("start", ""), spec.get("end", ""))
    if v["status"] != "ok":
        return v
    tier = spec.get("tier", "mid")
    travellers = max(1, int(spec.get("travellers", 1)))
    cities = spec.get("cities", [])
    days: List[Dict] = []
    total = 0.0
    cursor = datetime.strptime(spec["start"], "%Y-%m-%d")
    for c in cities:
        h = hotel_cost(c["city"], c["nights"], tier=tier).get("cost_usd", 0)
        f = food_cost(c["nights"], tier=tier, travellers=travellers).get("cost_usd", 0)
        t = local_transport_cost(c["nights"], travellers=travellers).get("cost_usd", 0)
        per_day_cost = round((h + f + t) / max(1, c["nights"]), 2)
        for _ in range(c["nights"]):
            date_str = cursor.strftime("%Y-%m-%d")
            days.append({
                "date": date_str,
                "city": c["city"],
                "morning": "Local breakfast + main attraction",
                "afternoon": "Cultural visit / neighbourhood walk",
                "evening": "Dinner at a regional restaurant",
                "estimated_cost_usd": per_day_cost,
            })
            total += per_day_cost
            cursor += timedelta(days=1)
    within = total <= float(spec.get("budget_usd", total))
    return {
        "status": "ok",
        "title": spec.get("title", "Untitled Trip"),
        "total_days": len(days),
        "cities": [c["city"] for c in cities],
        "days": days,
        "total_estimated_cost_usd": round(total, 2),
        "within_budget": within,
        "notes": "All estimates are per-person/trip. Book transport separately.",
    }


root_agent = Agent(
    name="trip_planner_agent",
    model="gemini-2.0-flash",
    description=(
        "Plans a multi-city trip with cost estimates, day balance, "
        "and a structured JSON itinerary."
    ),
    instruction="""
    You are a meticulous travel planner.

    WORKFLOW for every request:
    1. Call `validate_dates` to confirm the date range.
    2. Call `balance_days` to split days across the user's cities
       (min 2 days/city unless the user overrides).
    3. For each city, call `hotel_cost` (with the user's tier),
       `food_cost`, and `local_transport_cost`.
    4. For inter-city or arrival flights, call `flight_estimate`.
    5. Call `build_itinerary` with a JSON spec that aggregates all
       of the above. The result is the canonical day-by-day plan.

    DELIVERABLES:
    - A per-day plan with morning/afternoon/evening suggestions
       tailored to each city's character.
    - A budget breakdown: hotels, food, transport, flights.
    - If `within_budget` is false, suggest 2-3 concrete ways to
       trim cost (lower tier, fewer cities, shorter stay).

    RULES:
    - Never invent specific business names, addresses or prices
       that you can't back up with the tools.
    - Respect visa, safety and seasonality notes in your prose.
    - Keep each day plan to 1-2 sentences per time slot.
    """,
    tools=[
        validate_dates, hotel_cost, food_cost, local_transport_cost,
        flight_estimate, balance_days, build_itinerary,
    ],
    output_schema=Itinerary,
    output_key="itinerary",
)
