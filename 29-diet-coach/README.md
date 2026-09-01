# Diet Coach Agent

A pure-Python ADK agent that turns a user's stats (weight, height,
age, sex, activity, goal) and diet preference into a **single-day
meal plan** with calories and macros, plus substitutions and a
shopping list.

## Tools

| Tool | Purpose |
| --- | --- |
| `food_info(food)` | Macros per serving. |
| `list_foods(tag="")` | Browse the built-in food database. |
| `substitute(food, exclude_tags="")` | Same-slot alternatives. |
| `daily_target(weight_kg, height_cm, age, sex, activity, goal)` | Mifflin-St Jeor BMR + TDEE + goal-adjusted kcal. |
| `build_meal_plan(target_kcal, diet="omnivore")` | Greedy slot-filler. |
| `shopping_list(plan_json)` | Convert plan JSON to shopping list. |

The food database is intentionally tiny (~20 staples). It is meant
to demonstrate the pattern; swap `_FOODS` for a real database to
productionize.

## Project Structure

```
29-diet-coach/
└── diet_coach_agent/
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

- "I'm 80kg, 175cm, 32M, moderately active and want to lose weight.
  Build me a 2000 kcal vegan day."
- "Substitute lentils for something with more protein."
- "What foods do I have to buy for that plan?"
