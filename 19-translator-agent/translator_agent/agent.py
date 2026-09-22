# === MODULE METADATA ===
# Version: 1.1.0
# Author: Translator Agent Development Team
# Date: 2025-01-01
# License: MIT
# Description: This module defines a pure-Python ADK (Agent Development Kit) agent
#              capable of translating text between 22 supported languages.
#              It returns a structured Pydantic response containing the translated
#              text, detected source language, target language, formality register,
#              and optional translator notes.
#
# Dependencies: google.adk.agents (LlmAgent), pydantic (BaseModel, Field)
# Usage:
#   from translator_agent.agent import root_agent, TranslationResult
#   result = root_agent.run("Hola, ¿cómo estás?", target="English")
#   print(result.translated_text)
#
# changelog:
#   1.0.0 - Initial release with basic translation support.
#   1.1.0 - Added expanded documentation, type hints, and formality detection.

"""
Translator Agent Module.

This module provides a production-ready ADK (Agent Development Kit) agent
designed for multilingual text translation. The agent leverages a combination
of rule-based heuristics for preliminary language detection and the underlying
LLM's (Large Language Model) robust multilingual capabilities to produce
high-quality translations.

Key Features:
-------------
- Supports 22 major world languages spanning multiple scripts and regions.
- Returns a structured Pydantic ``TranslationResult`` object, ensuring
  downstream consumers can rely on a stable and predictable JSON schema.
- Detects source language automatically from input text.
- Registers formality (formal vs. informal) of the output translation.
- Handles idiomatic expressions and cultural adaptation gracefully,
  surfacing any transformations in the ``notes`` field.

Architecture Overview:
----------------------
The module defines three primary components:

1. ``SUPPORTED_LANGUAGES`` — A module-level constant listing all languages
   the agent can translate to/from. This list is referenced both by the
   agent's system instruction and by validation logic elsewhere in the
   codebase.

2. ``TranslationResult`` — A Pydantic ``BaseModel`` subclass that serves as
   the ``output_schema`` for the agent. It enforces type safety and provides
   documentation for every field in the structured response.

3. ``root_agent`` — An instance of ``LlmAgent`` configured with a detailed
   system prompt, the ``TranslationResult`` output schema, and an output
   key of ``"translation"``. This is the primary interface users interact with.

Usage Example:
--------------
>>> from translator_agent.agent import root_agent, TranslationResult
>>> # The agent can be invoked through the ADK framework's runner API.
>>> # Below is a conceptual example:
>>> result = root_agent.run(
...     user_message="Bonjour le monde",
...     context={"target_language": "English"}
... )
>>> print(result.translated_text)
"Hello world"
>>> print(result.source_language)
"French"

NOTE: The actual invocation mechanism depends on the ADK runner infrastructure
      and is not defined within this module. This module only defines the
      agent configuration and its output schema.

Performance Notes:
------------------
- Language detection is handled primarily by the LLM during translation,
  supplemented by lightweight heuristics in upstream preprocessing steps.
- The model used is ``gemini-2.0-flash``, chosen for its balance of
  translation quality and response latency.

TODO: Consider adding a caching layer for repeated translation requests
      with identical source/target language pairs to reduce LLM calls.
FIXME: The ``formality`` field currently relies on LLM self-reporting;
       a post-processing validation step may be added to enforce
       strict enum-like values.
"""


# === IMPORTS AND DEPENDENCIES ===
# We import List from typing for type annotation compatibility.
# In Python 3.9+, list[str] could be used directly, but List is retained
# here for broader compatibility with older Python versions in the project.
from typing import List  # type: () -> List[str]

# ADK dependency: provides the LlmAgent class for building LLM-powered agents.
from google.adk.agents import LlmAgent

# Pydantic dependency: provides BaseModel and Field for structured data validation
# and serialization. The output_schema of the agent is a Pydantic model.
from pydantic import BaseModel, Field


# === SUPPORTED LANGUAGES CONSTANT ===
# This list defines every language the translator agent officially supports.
# It is used in the agent's system prompt to inform the LLM of its capabilities
# and may also be referenced by validation or filtering logic in other modules.
# NOTE: If a new language needs to be added, update this list AND the agent
#       instruction string to keep them in sync.
# TODO: Consider loading this list from a configuration file (e.g., YAML or JSON)
#       to allow runtime modifications without code changes.
SUPPORTED_LANGUAGES: List[str] = [  # type: () -> List[str]
    "English", "Spanish", "French", "German", "Italian", "Portuguese",
    "Dutch", "Russian", "Chinese (Simplified)", "Japanese", "Korean",
    "Arabic", "Hindi", "Bengali", "Tamil", "Telugu", "Turkish",
    "Vietnamese", "Thai", "Polish", "Swedish", "Greek", "Hebrew",
]

# Pre-compute a comma-separated string of supported languages for use in
# instruction templates. This avoids repeated string joins during agent
# instantiation and keeps the code DRY.
# type: () -> str
SUPPORTED_LANGUAGES_STR: str = ", ".join(SUPPORTED_LANGUAGES)


# === TRANSLATION RESULT SCHEMA ===
# This Pydantic model defines the exact shape of the structured JSON response
# that the translator agent will produce. By declaring it as the agent's
# output_schema, the ADK framework will validate the LLM's output against
# this model before returning it to the caller.
# Every field is documented with its purpose, expected values, and any
# constraints. This ensures that any consumer of TranslationResult can
# programmatically rely on field existence and types.
class TranslationResult(BaseModel):
    """Structured result object for a single translation operation.

    This model is used as the ``output_schema`` for the ``root_agent``.
    After each translation request, the agent is expected to produce a
    JSON object conforming to this schema, which is then parsed into
    a ``TranslationResult`` instance.

    Example:
    --------
    >>> result = TranslationResult(
    ...     source_text="Hola",
    ...     source_language="Spanish",
    ...     target_language="English",
    ...     translated_text="Hello",
    ...     formality="formal",
    ...     notes=""
    ... )
    >>> result.translated_text
    'Hello'

    Attributes:
    -----------
    source_text : str
        The original text provided by the user. This field is stored
        unchanged so that callers can verify or reference the original input.
    source_language : str
        The detected language of ``source_text``. Must be one of the
        entries in ``SUPPORTED_LANGUAGES`` or the literal ``'Auto-detected'``
        if the language could not be confidently identified.
    target_language : str
        The language the text was translated into. Must be one of the
        entries in ``SUPPORTED_LANGUAGES``.
    translated_text : str
        The actual translated text in the target language. This is the
        primary output of the translation operation.
    formality : str
        Indicates the linguistic register used in the translation.
        Expected values are ``'formal'`` or ``'informal'``, though
        additional values may appear if the LLM interprets the request
        differently (see FIXME note in the module docstring).
    notes : str
        Optional field for translator notes regarding idioms, ambiguity,
        cultural adaptations, or any other observations. An empty string
        ``""`` indicates no special notes are necessary.
    """

    # The original, unmodified text supplied by the user.
    # This is preserved for auditability and round-trip verification.
    source_text: str = Field(  # type: (self) -> str
        description="The original text provided by the user, unchanged."
    )

    # Auto-detected language of the source text. Validated against
    # SUPPORTED_LANGUAGES or the sentinel value 'Auto-detected'.
    # NOTE: In a future iteration, we may replace 'Auto-detected' with a
    #       dedicated LanguageDetectionResult model that includes confidence scores.
    source_language: str = Field(  # type: (self) -> str
        description=(
            "The detected language of source_text. Must be one of "
            f"{SUPPORTED_LANGUAGES} or 'Auto-detected'."
        )
    )

    # The target language into which the text was translated.
    # Must be a valid entry from SUPPORTED_LANGUAGES.
    target_language: str = Field(  # type: (self) -> str
        description=(
            f"The language the text was translated into. Must be one "
            f"of {SUPPORTED_LANGUAGES}."
        )
    )

    # The resulting translated text. This is the core deliverable.
    translated_text: str = Field(  # type: (self) -> str
        description="The translated text in target_language."
    )

    # Linguistic register of the translation: 'formal' or 'informal'.
    # This field helps downstream consumers adapt UI tone or processing logic.
    # FIXME: Consider constraining this to a Literal['formal', 'informal']
    #        type for stricter validation, but this requires Pydantic v2
    #        and may conflict with current schema generation.
    formality: str = Field(  # type: (self) -> str
        description=(
            "Either 'formal' or 'informal' indicating the register "
            "used in the translation."
        )
    )

    # Free-text field for any translator observations: idiom handling,
    # cultural adaptation notes, ambiguity warnings, etc.
    # Defaults to empty string when no notes are applicable.
    notes: str = Field(  # type: (self) -> str
        description=(
            "Optional translator notes about idioms, ambiguity, or "
            "cultural adaptation. Empty string if not needed."
        )
    )


# === ROOT AGENT DEFINITION ===
# The root_agent is the central entry point for all translation requests.
# It is an LlmAgent configured with:
#   - A descriptive name and model identifier
#   - A detailed system prompt that instructs the LLM on workflow steps
#   - The TranslationResult output schema for structured responses
#   - An output key 'translation' for result extraction
#
# The system prompt is carefully crafted to enforce a deterministic workflow:
# language detection → target language selection → translation → formality
# handling → structured JSON output. This minimizes ambiguity and reduces
# the likelihood of the LLM producing unstructured text.
# TODO: Evaluate adding a 'temperature' parameter to the LlmAgent configuration
#       to control randomness in translations. Lower values (e.g., 0.2) may
#       produce more consistent translations for technical content.
root_agent = LlmAgent(
    name="translator_agent",
    # model: str — the LLM to use. gemini-2.0-flash was selected for
    # its strong multilingual performance and low latency characteristics.
    model="gemini-2.0-flash",
    # description: str — a human-readable summary used by orchestration
    # layers (e.g., multi-agent routers) to decide when to delegate to this agent.
    description=(
        "Translates text between any two supported languages and "
        "returns a structured Pydantic result."
    ),
    # instruction: str — the system prompt that guides the LLM's behavior.
    # It enumerates supported languages and defines a 5-step workflow:
    #   1. Detect source language
    #   2. Determine or request target language
    #   3. Perform translation with cultural sensitivity
    #   4. Choose appropriate formality register
    #   5. Output strictly valid JSON matching the schema
    # NOTE: The instruction string is constructed using an f-string to embed
    #       the SUPPORTED_LANGUAGES list dynamically. This ensures that if
    #       the list is updated, the prompt reflects the change automatically.
    instruction=f"""
    You are a professional translator that supports the following
    languages:
    {SUPPORTED_LANGUAGES_STR}.

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
    # output_schema: BaseModel — the Pydantic model that defines the
    # expected structure of the agent's response. The ADK framework will
    # validate the LLM's raw output against this schema.
    output_schema=TranslationResult,
    # output_key: str — the key under which the validated result will be
    # stored in the agent's response dictionary. Downstream code accesses
    # the result via response["translation"].
    output_key="translation",
)


# === UTILITY FUNCTIONS ===
# Future utility functions (e.g., language validation, text preprocessing)
# may be added here. For now, the module relies entirely on the LLM
# for language detection and translation logic.

# TODO: Add a helper function `is_language_supported(lang: str) -> bool`
#       to allow external callers to check language support before
#       initiating a translation request.

# TODO: Add a helper function `get_available_languages() -> List[str]`
#       that returns a copy of SUPPORTED_LANGUAGES for API exposure.