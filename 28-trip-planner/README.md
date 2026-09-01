# Trip Planner Agent

A pure-Python ADK agent that converts a travel brief (cities, dates,
budget, traveller count, hotel tier) into a **validated, day-by-day
JSON itinerary** with cost estimates and a budget check.

## Tools

| Tool | Purpose |
| --- | --- |
| `validate_dates(start, end)` | Confirm ISO range, return day count. |
| `hotel_cost(city, nights, tier)` | Per-stay hotel estimate. |
| `food_cost(days, tier, travellers)` | Per-trip food estimate. |
| `local_transport_cost(days, travellers)` | Per-trip local transit. |
| `flight_estimate(origin, dest, travellers, class)` | Rough flight cost. |
| `balance_days(cities_json, total_days)` | Distribute days across cities. |
| `build_itinerary(spec_json)` | Assemble the final day-by-day plan. |

The agent is configured with `output_schema=Itinerary`, so its
final reply is guaranteed to be a valid JSON object shaped like:

```json
{
  "title": "Iberia 7-day",
  "total_days": 7,
  "cities": ["Lisbon", "Seville"],
  "days": [
    {"date": "2026-10-01", "city": "Lisbon",
     "morning": "...", "afternoon": "...", "evening": "...",
     "estimated_cost_usd": 180.0}
  ],
  "total_estimated_cost_usd": 2380.0,
  "within_budget": true,
  "notes": "..."
}
```

## Project Structure

```
28-trip-planner/
└── trip_planner_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```

## Example Prompts

- "Plan a 7-day Iberian trip for 2 in October, mid-tier hotels,
  budget $3500."
- "Distribute 10 days across Rome, Florence and Venice with at
  least 2 days in each."
- "Estimate flights and hotels for a 5-day Tokyo trip in November."
