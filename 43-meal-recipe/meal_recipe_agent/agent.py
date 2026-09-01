"""Pantry-to-Recipe Agent.

Given a list of pantry items, the agent scores a small built-in
recipe database by overlap and returns the top suggestions with
missing-ingredient lists.
"""

import json
import re
from collections import Counter
from typing import Dict, List, Set

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class RecipeSuggestion(BaseModel):
    title: str
    cuisine: str
    minutes: int
    matched: int
    total: int
    coverage_pct: float
    missing: List[str]
    instructions: List[str]


_RECIPES = [
    {
        "title": "Lentil Soup",
        "cuisine": "mediterranean",
        "minutes": 30,
        "ingredients": ["lentils", "onion", "carrot", "celery", "garlic", "olive_oil", "tomato"],
        "instructions": [
            "Dice onion, carrot, celery, garlic.",
            "Sweat in olive oil for 5 min.",
            "Add lentils + diced tomato + 1.5L water.",
            "Simmer 25 min until lentils are tender.",
        ],
    },
    {
        "title": "Veggie Stir Fry",
        "cuisine": "asian",
        "minutes": 15,
        "ingredients": ["broccoli", "carrot", "garlic", "ginger", "soy_sauce", "olive_oil", "rice"],
        "instructions": [
            "Cook rice.",
            "Stir-fry garlic + ginger in oil.",
            "Add broccoli + carrot; toss 4 min.",
            "Splash soy sauce; serve over rice.",
        ],
    },
    {
        "title": "Pasta Aglio e Olio",
        "cuisine": "italian",
        "minutes": 20,
        "ingredients": ["pasta", "garlic", "olive_oil", "chili", "parsley", "parmesan"],
        "instructions": [
            "Boil pasta in salted water.",
            "Sizzle garlic + chili in olive oil.",
            "Toss pasta in the oil with a splash of pasta water.",
            "Top with parsley + parmesan.",
        ],
    },
    {
        "title": "Tofu Bowl",
        "cuisine": "asian",
        "minutes": 20,
        "ingredients": ["tofu", "rice", "broccoli", "soy_sauce", "garlic", "sesame_oil"],
        "instructions": [
            "Press and cube tofu.",
            "Pan-fry until golden.",
            "Steam broccoli; cook rice.",
            "Assemble with soy + sesame oil drizzle.",
        ],
    },
    {
        "title": "Bean Quesadilla",
        "cuisine": "mexican",
        "minutes": 15,
        "ingredients": ["tortilla", "beans", "cheese", "onion", "salsa"],
        "instructions": [
            "Mash beans with diced onion.",
            "Spread on tortilla; top with cheese.",
            "Toast both sides in a dry pan.",
            "Serve with salsa.",
        ],
    },
]


def parse_pantry(text: str) -> dict:
    """Parse a comma- or newline-separated pantry list into a normalised set."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    parts = re.split(r"[,\n;]+", text.lower())
    items: Set[str] = sorted({p.strip().replace(" ", "_") for p in parts if p.strip()})
    return {"status": "ok", "items": list(items), "count": len(items)}


def score_recipe(pantry_json: str, recipe: Dict) -> dict:
    """Return the overlap between pantry items and a recipe's ingredients."""
    try:
        pantry = {x.lower().replace(" ", "_") for x in json.loads(pantry_json)}
    except (ValueError, TypeError) as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    ings = {i.lower() for i in recipe["ingredients"]}
    matched = pantry & ings
    missing = sorted(ings - pantry)
    cov = round(100 * len(matched) / max(1, len(ings)), 1)
    return {
        "status": "ok",
        "title": recipe["title"],
        "cuisine": recipe["cuisine"],
        "minutes": recipe["minutes"],
        "matched": len(matched),
        "total": len(ings),
        "coverage_pct": cov,
        "missing": missing,
        "instructions": recipe["instructions"],
    }


def suggest(pantry_text: str, top_n: int = 3, min_coverage: float = 30.0) -> dict:
    """Return the top-N recipes that overlap with the pantry."""
    pp = parse_pantry(pantry_text)
    if pp["status"] != "ok":
        return pp
    pantry_json = json.dumps(pp["items"])
    scored = [score_recipe(pantry_json, r) for r in _RECIPES]
    scored = [s for s in scored if s.get("coverage_pct", 0) >= min_coverage]
    scored.sort(key=lambda s: (s["coverage_pct"], -s["minutes"]), reverse=True)
    n = max(1, min(int(top_n), len(scored)))
    return {
        "status": "ok",
        "pantry": pp["items"],
        "count": len(scored),
        "suggestions": scored[:n],
    }


def shopping_list(suggestion_json: str) -> dict:
    """Aggregate missing ingredients across multiple suggestions into one list."""
    try:
        sugg = json.loads(suggestion_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(sugg, list):
        return {"status": "error", "error": "expected a JSON list of suggestions."}
    counts: Counter = Counter()
    for s in sugg:
        for m in s.get("missing", []):
            counts[m] += 1
    items = [{"item": k, "needed_for": v} for k, v in counts.most_common()]
    return {"status": "ok", "items": items, "unique_count": len(items)}


def categorize_missing(items_json: str) -> dict:
    """Bucket missing items by store aisle (rough heuristic)."""
    try:
        items = [x.lower() for x in json.loads(items_json)]
    except (ValueError, TypeError) as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(items, list):
        return {"status": "error", "error": "expected a JSON list."}
    buckets = {"produce": [], "grains": [], "dairy": [], "pantry": [], "spice": [], "other": []}
    PRODUCE = {"onion", "garlic", "ginger", "broccoli", "carrot", "celery", "parsley", "tomato"}
    GRAINS = {"rice", "pasta", "tortilla", "lentils", "beans"}
    DAIRY = {"parmesan", "cheese"}
    PANTRY = {"olive_oil", "sesame_oil", "soy_sauce", "salsa"}
    SPICE = {"chili", "salt", "pepper"}
    for i in items:
        if i in PRODUCE: buckets["produce"].append(i)
        elif i in GRAINS: buckets["grains"].append(i)
        elif i in DAIRY: buckets["dairy"].append(i)
        elif i in PANTRY: buckets["pantry"].append(i)
        elif i in SPICE: buckets["spice"].append(i)
        else: buckets["other"].append(i)
    return {k: v for k, v in buckets.items() if v}


root_agent = Agent(
    name="meal_recipe_agent",
    model="gemini-2.0-flash",
    description=(
        "Suggests recipes that match the user's pantry, lists the "
        "missing ingredients, and groups them by store aisle."
    ),
    instruction="""
    You are a budget-friendly meal-planning assistant.

    WORKFLOW:
    1. Call `parse_pantry` on the user's comma/newline-separated
       pantry list.
    2. Call `suggest` with top_n=3 to get the best matches.
    3. Call `shopping_list` and `categorize_missing` to build the
       shopping view.

    DELIVERABLES:
    - Top 3 recipe suggestions, each with: title, cuisine, time,
      coverage %, and missing-ingredient list.
    - A combined shopping list grouped by aisle.
    - 1-2 sentence meal-prep tip (e.g. "cook the rice once and
      reuse it for the stir fry and tofu bowl").

    RULES:
    - Only use recipes from the built-in database; never invent
       ingredients.
    - If a recipe requires more than 5 missing items, mark it
       "(long shopping list)" in the prose.
    - Respect the user's `min_coverage` override if they set one.
    """,
    tools=[
        parse_pantry, score_recipe, suggest, shopping_list,
        categorize_missing,
    ],
    output_schema=RecipeSuggestion,
    output_key="recipe",
)
