# Translator Agent

A pure-Python ADK agent that translates text between 20+ languages
and returns a **structured Pydantic** response. The schema is fixed
up-front so downstream code can parse the agent's reply as JSON.

## Output Schema

```python
class TranslationResult(BaseModel):
    source_text: str        # original input, unchanged
    source_language: str    # detected source language
    target_language: str    # language translated into
    translated_text: str    # the translation itself
    formality: str          # "formal" or "informal"
    notes: str              # any cultural / idiom notes
```

## Supported Languages

English, Spanish, French, German, Italian, Portuguese, Dutch,
Russian, Chinese (Simplified), Japanese, Korean, Arabic, Hindi,
Bengali, Tamil, Telugu, Turkish, Vietnamese, Thai, Polish, Swedish,
Greek, Hebrew.

## Project Structure

```
19-translator-agent/
└── translator_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + Pydantic schema
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
4. Select **translator_agent** from the dropdown.

## Example Prompts to Try

- "Translate this to French (formal): 'Thank you for your prompt
  response.'"
- "How do you say 'Where is the nearest metro station?' in Japanese?"
- "Translate the following Hindi sentence to English and explain
  any idioms: ..."
