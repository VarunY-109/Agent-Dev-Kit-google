# Calculator Agent

A pure-Python ADK agent that performs **exact** arithmetic by
delegating every computation to Python's own `ast` parser. The LLM
handles the natural-language front-end, but the actual math is
always run by the tools - so the agent never gets "2 + 2 = 5".

## Tools

| Tool | Purpose |
| --- | --- |
| `calculate(expression)` | Safely evaluate a Python arithmetic expression. |
| `unit_convert(value, src, dst, kind="")` | Convert between length, mass, data, and temperature units. |
| `percentage(part, whole, mode="of")` | Compute percent-of, is-what-percent, and percent change. |

The expression evaluator is a **strict whitelist**:

* only the binary operators `+ - * / // % **` are allowed
* only the unary `+` and `-` are allowed
* only Python `math.*` functions and the constants `pi`, `e`, `tau`
  are in scope - no attribute access, no imports, no name lookups.

## Project Structure

```
20-calculator-agent/
└── calculator_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + math tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **calculator_agent** from the dropdown.

## Example Prompts to Try

- "What is 17 * 23 + 49?"
- "Compute 15% tip on a $84.50 bill."
- "Convert 100 miles to kilometers."
- "If a stock went from $48 to $61, what's the percent change?"
- "What is the hypotenuse of a right triangle with legs 3 and 4?"
