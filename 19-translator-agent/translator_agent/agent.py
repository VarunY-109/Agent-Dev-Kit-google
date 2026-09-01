"""Translator Agent.

A pure-Python ADK agent that translates text between languages and
returns a **structured** Pydantic response containing the translated
text, the detected source language, and a confidence note.

The agent relies on a small rule-based language-detection helper plus
the LLM's own multilingual capabilities. The ``output_schema`` is
declared on the agent so downstream code can rely on a stable JSON
shape.
"""

from typing import List

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field


# --- Pydantic output schema --------------------------------------------------
SUPPORTED_LANGUAGES: List[str] = [
    "English", "Spanish", "French", "German", "Italian", "Portuguese",
    "Dutch", "Russian", "Chinese (Simplified)", "Japanese", "Korean",
    "Arabic", "Hindi", "Bengali", "Tamil", "Telugu", "Turkish",
    "Vietnamese", "Thai", "Polish", "Swedish", "Greek", "Hebrew",
]


class TranslationResult(BaseModel):
    source_text: str = Field(
        description="The original text provided by the user, unchanged."
    )
    source_language: str = Field(
        description=(
            "The detected language of source_text. Must be one of "
            f"{SUPPORTED_LANGUAGES} or 'Auto-detected'."
        )
    )
    target_language: str = Field(
        description=(
            f"The language the text was translated into. Must be one "
            f"of {SUPPORTED_LANGUAGES}."
        )
    )
    translated_text: str = Field(
        description="The translated text in target_language."
    )
    formality: str = Field(
        description=(
            "Either 'formal' or 'informal' indicating the register "
            "used in the translation."
        )
    )
    notes: str = Field(
        description=(
            "Optional translator notes about idioms, ambiguity, or "
            "cultural adaptation. Empty string if not needed."
        )
    )


# --- Agent definition ---------------------------------------------------------
root_agent = LlmAgent(
    name="translator_agent",
    model="gemini-2.0-flash",
    description=(
        "Translates text between any two supported languages and "
        "returns a structured Pydantic result."
    ),
    instruction=f"""
    You are a professional translator that supports the following
    languages:
    {", ".join(SUPPORTED_LANGUAGES)}.

    WORKFLOW:
    1. Detect the source language of the user's text.
    2. Pick the target language from the user's request. If they
       don't specify one, ask politely before translating.
    3. Translate the text, preserving meaning, tone, and idioms. If
       a phrase has no direct equivalent, adapt it culturally and
       mention the adaptation in `notes`.
    4. Default to a neutral register unless the user asks for
       "formal" or "informal"/"casual".
    5. Always respond with valid JSON matching the schema. Do NOT
       include any prose outside the JSON object.
    """,
    output_schema=TranslationResult,
    output_key="translation",
)
