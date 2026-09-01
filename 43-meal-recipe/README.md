# Pantry-to-Recipe Agent

A pure-Python ADK agent that suggests recipes that match the
user's pantry, lists missing ingredients, and groups them by
store aisle.

## Tools

| Tool | Purpose |
| --- | --- |
| `parse_pantry(text)` | Normalise a comma/newline-separated list. |
| `score_recipe(pantry_json, recipe)` | Per-recipe overlap. |
| `suggest(pantry_text, top_n=3, min_coverage=30)` | Top-N suggestions. |
| `shopping_list(suggestion_json)` | Combined missing-ingredient list. |
| `categorize_missing(items_json)` | Group by aisle. |

## Built-in Recipes

| Title | Cuisine | Time |
| --- | --- | --- |
| Lentil Soup | Mediterranean | 30 min |
| Veggie Stir Fry | Asian | 15 min |
| Pasta Aglio e Olio | Italian | 20 min |
| Tofu Bowl | Asian | 20 min |
| Bean Quesadilla | Mexican | 15 min |

## Project Structure

```
43-meal-recipe/
└── meal_recipe_agent/
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

- "My pantry has: lentils, onion, garlic, olive oil, carrot. What can I make?"
- "Suggest 3 recipes using rice, broccoli, soy sauce, tofu."
- "Group the missing ingredients by aisle."
