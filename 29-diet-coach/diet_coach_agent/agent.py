"""Diet Coach Agent.

Builds a daily meal plan that hits a user-specified calorie and
macro target, using a small built-in food database and a greedy
slot-filling algorithm. The agent also surfaces substitution
suggestions and a shopping list.
"""

import json
from typing import Dict, List

from google.adk.agents import Agent


_FOODS: Dict[str, Dict] = {
    "oatmeal":      {"kcal": 150, "p": 5,  "c": 27, "f": 3,  "tags": ["breakfast", "vegan"]},
    "greek_yogurt": {"kcal": 100, "p": 17, "c": 6,  "f": 0,  "tags": ["breakfast", "vegetarian"]},
    "egg":          {"kcal": 78,  "p": 6,  "c": 1,  "f": 5,  "tags": ["breakfast", "vegetarian"]},
    "banana":       {"kcal": 105, "p": 1,  "c": 27, "f": 0,  "tags": ["snack", "vegan"]},
    "almonds":      {"kcal": 165, "p": 6,  "c": 6,  "f": 14, "tags": ["snack", "vegan"]},
    "chicken_breast": {"kcal": 165, "p": 31, "c": 0,  "f": 4,  "tags": ["lunch", "dinner"]},
    "salmon":       {"kcal": 208, "p": 22, "c": 0,  "f": 13, "tags": ["dinner"]},
    "tofu":         {"kcal": 144, "p": 17, "c": 3,  "f": 9,  "tags": ["lunch", "dinner", "vegan"]},
    "lentils":      {"kcal": 230, "p": 18, "c": 40, "f": 1,  "tags": ["lunch", "dinner", "vegan"]},
    "brown_rice":   {"kcal": 216, "p": 5,  "c": 45, "f": 2,  "tags": ["side", "vegan"]},
    "sweet_potato": {"kcal": 180, "p": 4,  "c": 41, "f": 0,  "tags": ["side", "vegan"]},
    "broccoli":     {"kcal": 55,  "p": 4,  "c": 11, "f": 1,  "tags": ["side", "vegan"]},
    "salad":        {"kcal": 60,  "p": 2,  "c": 8,  "f": 2,  "tags": ["side", "vegan"]},
    "olive_oil":    {"kcal": 120, "p": 0,  "c": 0,  "f": 14, "tags": ["fat", "vegan"]},
    "avocado":      {"kcal": 240, "p": 3,  "c": 12, "f": 22, "tags": ["fat", "vegan"]},
    "protein_shake":{"kcal": 160, "p": 25, "c": 8,  "f": 3,  "tags": ["snack"]},
    "apple":        {"kcal": 95,  "p": 0,  "c": 25, "f": 0,  "tags": ["snack", "vegan"]},
    "paneer":       {"kcal": 265, "p": 18, "c": 3,  "f": 21, "tags": ["lunch", "dinner", "vegetarian"]},
}


def _macros(food: str, servings: float = 1.0) -> Dict:
    info = _FOODS[food]
    return {k: round(v * servings, 2) for k, v in info.items() if k in {"kcal", "p", "c", "f"}}


def food_info(food: str) -> dict:
    """Return macros (per serving) for a known food."""
    info = _FOODS.get(food)
    if not info:
        return {"status": "error", "error": f"unknown food: {food!r}"}
    return {"status": "ok", "food": food, **{k: v for k, v in info.items() if k in {"kcal", "p", "c", "f"}}, "tags": info["tags"]}


def list_foods(tag: str = "") -> dict:
    """List all known foods, optionally filtered by tag (vegan, snack, ...)."""
    if not tag:
        items = sorted(_FOODS.keys())
    else:
        items = sorted(f for f, v in _FOODS.items() if tag in v["tags"])
    return {"status": "ok", "count": len(items), "foods": items}


def substitute(food: str, exclude_tags: str = "") -> dict:
    """Suggest similar foods (same primary tag) that can replace ``food``."""
    info = _FOODS.get(food)
    if not info:
        return {"status": "error", "error": f"unknown food: {food!r}"}
    excl = {t.strip() for t in exclude_tags.split(",") if t.strip()}
    primary = info["tags"][0] if info["tags"] else ""
    alts = []
    for name, v in _FOODS.items():
        if name == food:
            continue
        if excl and any(t in excl for t in v["tags"]):
            continue
        if primary in v["tags"]:
            alts.append(name)
    return {"status": "ok", "food": food, "substitutes": alts}


def daily_target(weight_kg: float, height_cm: float, age: int, sex: str,
                 activity: str, goal: str = "maintain") -> dict:
    """Mifflin-St Jeor BMR + activity multiplier + goal adjustment."""
    try:
        w, h, a = float(weight_kg), float(height_cm), int(age)
    except (TypeError, ValueError):
        return {"status": "error", "error": "weight/height/age must be numbers."}
    s = (sex or "").lower()
    if s in ("m", "male"):
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    elif s in ("f", "female"):
        bmr = 10 * w + 6.25 * h - 5 * a - 161
    else:
        return {"status": "error", "error": "sex must be 'male' or 'female'."}
    mult = {
        "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
        "active": 1.725, "very_active": 1.9,
    }.get((activity or "").lower())
    if mult is None:
        return {"status": "error", "error": f"activity must be one of: sedentary/light/moderate/active/very_active"}
    tdee = bmr * mult
    adj = {"lose": -0.20, "maintain": 0.0, "gain": 0.15}.get((goal or "maintain").lower())
    if adj is None:
        return {"status": "error", "error": "goal must be lose/maintain/gain."}
    kcal = round(tdee * (1 + adj))
    return {
        "status": "ok",
        "bmr": round(bmr, 1),
        "tdee": round(tdee, 1),
        "target_kcal": kcal,
        "protein_g": round(w * 2.0),
        "carbs_g": round((kcal * 0.45) / 4),
        "fat_g": round((kcal * 0.30) / 9),
    }


_SLOT_TEMPLATES = {
    "breakfast": ["oatmeal", "greek_yogurt", "egg"],
    "lunch": ["chicken_breast", "tofu", "lentils", "paneer"],
    "dinner": ["salmon", "tofu", "chicken_breast", "lentils", "paneer"],
    "snack": ["banana", "almonds", "apple", "protein_shake"],
}


def build_meal_plan(target_kcal: int, diet: str = "omnivore") -> dict:
    """Greedy slot-filler that builds a single day hitting a calorie target."""
    try:
        target = int(target_kcal)
    except (TypeError, ValueError):
        return {"status": "error", "error": "target_kcal must be int."}
    diet = (diet or "omnivore").lower()
    excluded = {
        "vegan": {"vegetarian"},
        "vegetarian": set(),
        "omnivore": set(),
    }.get(diet)
    if excluded is None:
        return {"status": "error", "error": "diet must be omnivore/vegetarian/vegan."}

    plan: List[Dict] = []
    total_kcal = 0
    for slot, candidates in _SLOT_TEMPLATES.items():
        chosen = None
        for f in candidates:
            tags = set(_FOODS[f]["tags"])
            if tags & excluded:
                continue
            info = _macros(f)
            if total_kcal + info["kcal"] <= target + 50:
                chosen = f
                break
        if not chosen and candidates:
            for f in candidates:
                tags = set(_FOODS[f]["tags"])
                if tags & excluded:
                    continue
                chosen = f
                break
        if chosen:
            m = _macros(chosen)
            plan.append({"slot": slot, "food": chosen, **m})
            total_kcal += m["kcal"]
    return {
        "status": "ok",
        "diet": diet,
        "target_kcal": target,
        "total_kcal": round(total_kcal, 1),
        "plan": plan,
    }


def shopping_list(plan_json: str) -> dict:
    """Convert a meal plan JSON to a sorted shopping list."""
    try:
        plan = json.loads(plan_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    items = sorted({entry["food"] for entry in plan if "food" in entry})
    return {"status": "ok", "items": items, "count": len(items)}


root_agent = Agent(
    name="diet_coach_agent",
    model="gemini-2.0-flash",
    description=(
        "Builds a daily meal plan that hits a user-specified calorie "
        "and macro target, with substitutions and a shopping list."
    ),
    instruction="""
    You are a registered-dietitian-style meal planning assistant.

    WORKFLOW:
    1. If the user provides weight, height, age, sex, activity and
       goal, call `daily_target` to compute kcal and macros.
    2. Call `build_meal_plan` with the target kcal and the user's
       diet (omnivore/vegetarian/vegan).
    3. For each food the user can't or won't eat, call `substitute`
       to find a same-slot replacement.
    4. Call `shopping_list` to produce the final grocery list.

    DELIVERABLES:
    - Computed daily target (kcal + P/C/F split).
    - The meal plan with kcal per slot.
    - A concise shopping list.
    - 1-2 lines of coaching tied to the user's goal
       (e.g. "Protein is high - good for satiety on a cut").

    RULES:
    - All numeric macros come from the tools; never estimate them.
    - If the plan undershoots kcal by more than 15%, suggest adding
       a snack or larger portion rather than a new meal.
    - Respect declared allergies: the substitute tool can filter
       by excluded tags.
    """,
    tools=[
        food_info, list_foods, substitute, daily_target,
        build_meal_plan, shopping_list,
    ],
)
