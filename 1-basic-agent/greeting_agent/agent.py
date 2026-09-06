"""Greeting agent module using Google's ADK (Agent Development Kit).

Purpose:
    This module defines a simple conversational agent that interacts with users
    by asking for their name and responding with a personalized greeting.
    It serves as a foundational "Hello, World!"-style example for getting
    started with the Google Agent Development Kit (ADK). The agent demonstrates
    the minimal configuration required to wire up a model, an instruction
    prompt, and identifying metadata so the ADK can orchestrate user turns.

    The example is intentionally lightweight — no custom tools, no sub-agents,
    no state management — making it an ideal first project for developers
    exploring how the ADK loads and executes agents from a directory layout
    that follows the ``greeting_agent/agent.py`` convention.

Architecture Overview::

    +-------------------+
    |   User (Client)   |
    +---------+---------+
              |
              v   HTTP / CLI
    +---------+---------+        +--------------------+
    |   ADK Runtime     | -----> |   root_agent       |
    | (adk run / api_   |        | (this module)      |
    |  server)          | <----- |  - name            |
    +-------------------+        |  - model           |
                                 |  - instruction     |
                                 +---------+----------+
                                           |
                                           v
                                 +---------+----------+
                                 | gemini-2.0-flash   |
                                 | (Generative Model) |
                                 +--------------------+

Usage:
    The module is typically imported and executed via the ADK runtime.
    From a project root, you can run the agent locally with::

        adk run 1-basic-agent/greeting_agent

    Alternatively, you can start an API server for the agent with::

        adk api_server 1-basic-agent/greeting_agent

    Once the server is running, requests may be sent to the agent's endpoint
    with a user message such as ``"Hello!"`` and the agent will prompt for the
    user's name before replying with a personalized greeting.

    Programmatic import is also supported for testing or composition::

        from greeting_agent.agent import root_agent
        assert root_agent.name == "greeting_agent"

Example:
    >>> from greeting_agent.agent import root_agent
    >>> root_agent.name
    'greeting_agent'
    >>> root_agent.model
    'gemini-2.0-flash'
    >>> root_agent.description
    'Greeting agent'

Conversational Flow:
    1. User sends a message (e.g., ``"Hi there!"``).
    2. The ADK runtime forwards the message to ``root_agent``.
    3. The agent, guided by its ``instruction``, asks: ``"What is your name?"``
    4. User replies with their name (e.g., ``"Alice"``).
    5. The agent responds with a personalized greeting such as
       ``"Hello, Alice! Nice to meet you."``

Metadata:
    :author:  ADK Example Authors
    :version: 0.2.0
    :since:   2024
    :license: Apache-2.0
    :see_also:
        - Google ADK documentation: https://google.github.io/adk-docs/
        - Agent class reference: :class:`google.adk.agents.Agent`

Change Log:
    * 0.2.0 - Expanded documentation, added self-check block, added
      ``__all__`` declaration, added inline reasoning comments.
    * 0.1.0 - Initial release with minimal agent definition.
"""

# =====================================================================
# Imports
# =====================================================================

# Google ADK provides the ``Agent`` base class used to construct
# conversational agents backed by large language models. The ``Agent``
# class wires together a model identifier, instruction prompt, and
# metadata so the ADK runtime can orchestrate turns with the user.
#
# Importing ``Agent`` at module scope (rather than inside a function) is
# intentional: it ensures any import-time configuration issues are
# surfaced immediately, and avoids repeated import overhead if the
# module is reloaded across multiple test cases.
#
# type: (model: str, name: str, description: str, instruction: str) -> Agent
from google.adk.agents import Agent

# NOTE: If you need additional ADK primitives later (such as ``Tool``,
# ``SubAgent``, or ``Session``), add them to this section so reviewers
# can quickly see the module's external dependencies. Keeping imports
# centralized at the top of the file is also the convention enforced
# by most Python style guides (e.g., PEP 8).
#
# FIXME: None at this time, but watch for breaking changes in the
# ``google.adk.agents`` namespace across ADK minor versions.

# =====================================================================
# Constants
# =====================================================================

#: str: The machine-friendly identifier for this agent.
#
# This identifier is used by the ADK runtime for logging, agent
# dispatch, and as part of any generated trace or session record.
# Keep it stable across releases to avoid breaking saved sessions.
#
# The value is lower-snake-case to match ADK conventions and the
# surrounding directory name (``greeting_agent/``), which the runtime
# also uses to locate the module.
AGENT_NAME = "greeting_agent"

#: str: The identifier of the underlying generative model.
#
# Gemini 2.0 Flash was selected for its low-latency responses, which
# makes it well-suited for a conversational greeting scenario where
# snappy replies matter more than deep reasoning. See the Gemini
# model catalog for a list of alternatives if you need different
# latency/quality trade-offs (e.g., ``gemini-1.5-pro`` for richer
# responses at the cost of higher latency).
#
# NOTE: Changing this constant does NOT migrate existing sessions or
# cached prompts. Plan for that if you swap models in production.
AGENT_MODEL = "gemini-2.0-flash"

#: str: A short, human-readable description of the agent's purpose.
#
# The ADK runtime surfaces this string in agent listings, developer
# UIs, and auto-generated documentation. Keep it concise (a single
# sentence). If you localize the agent, consider providing translations
# of this string in a dedicated ``descriptions`` mapping rather than
# editing the constant in place.
AGENT_DESCRIPTION = "Greeting agent"

#: str: The natural-language system prompt that guides the model's
#: behavior.
#
# Multi-line strings are preserved verbatim, including the leading
# whitespace and newlines, so the model receives the formatted
# instructions exactly as authored below.
#
# The instruction is deliberately short to minimize token usage on
# every turn. If you find the model straying from the desired
# behavior, consider expanding the instruction with explicit examples
# rather than adding post-processing logic.
#
# The trailing whitespace on the first line and the newline at the
# end are intentional formatting choices — they make the rendered
# prompt read naturally in both the model log and any debug view.
AGENT_INSTRUCTION = """
    You are a helpful assistant that greets the user. 
    Ask for the user's name and greet them by name.
    """

# =====================================================================
# Agent Definition
# =====================================================================

# Initialize the root agent responsible for greeting users.
#
# NOTE: The ``root_agent`` name is a conventional identifier expected
# by the ADK runtime. When the module is loaded by ``adk run`` or
# ``adk api_server``, the runtime looks up this attribute to determine
# which agent should handle incoming user requests. Renaming it will
# likely cause the agent to be invisible to the ADK entry points.
#
# The agent is configured with:
#   * ``name``         - A short, machine-friendly identifier used in
#                        logs and tool dispatch.
#   * ``model``        - The underlying generative model. Gemini 2.0
#                        Flash is selected for its low-latency
#                        responses, which makes it well-suited for a
#                        conversational greeting scenario where snappy
#                        replies matter more than deep reasoning.
#   * ``description``  - A human-readable summary describing what the
#                        agent does; surfaced in agent listings and
#                        UIs.
#   * ``instruction``  - The natural-language system prompt that
#                        guides the model's behavior. Here, the agent
#                        is told to (1) ask for the user's name and
#                        (2) greet them using that name.
#
# Arguments:
#     name (str): The unique identifier for the agent within its
#         module. Must be a valid Python identifier-style string and
#         should remain stable across versions to preserve session
#         compatibility.
#     model (str): The fully-qualified model identifier. Must be a
#         model available to your project's credentials; otherwise the
#         agent will fail at first invocation with an authentication
#         error.
#     description (str): A one-sentence summary of the agent's
#         purpose. Used for documentation listings and developer
#         tooling.
#     instruction (str): The system prompt. May include newlines and
#         leading/trailing whitespace; the ADK passes it through to
#         the model without modification.
#
# Returns:
#     Agent: A configured agent instance. The object is ready to be
#     served by ``adk run`` or ``adk api_server`` and requires no
#     further setup.
#
# Raises:
#     ImportError: If the ``google.adk.agents`` package is not
#         installed. Install it via ``pip install google-adk`` and
#         retry.
#     pydantic.ValidationError: If any of the constructor arguments
#         fail ADK's schema validation (for example, an empty
#         ``name``).
#
# Examples:
#     >>> root_agent.name
#     'greeting_agent'
#     >>> root_agent.model
#     'gemini-2.0-flash'
#
# TODO: Consider extending the instructions to handle edge cases
# such as the user refusing to share their name or providing an empty
# input. A short list of fallback behaviors in the prompt can prevent
# awkward silences from the model.
# TODO: Add a unit test under ``tests/test_greeting_agent.py`` that
# uses the ADK's in-memory runner to verify the greeting flow
# end-to-end. Aim for at least one happy-path and one edge-case test.
# TODO: Explore wiring up a custom tool (e.g., ``set_user_name``) to
# persist the user's name in a session-scoped state object so that
# follow-up turns can reference the user without re-asking.
# FIXME: (None) No known issues at this time.
root_agent = Agent(  # type: Agent
    name=AGENT_NAME,
    model=AGENT_MODEL,
    description=AGENT_DESCRIPTION,
    instruction=AGENT_INSTRUCTION,
)

# =====================================================================
# Public API
# =====================================================================

# Expose the configured agent as the module's primary public symbol.
# Importers (including the ADK runtime) should reference
# ``root_agent`` rather than re-instantiating ``Agent`` themselves,
# so that the configuration above remains the single source of truth
# for this module's behavior.
#
# Defining ``__all__`` makes the public surface explicit. Tools that
# inspect this list (linters, documentation generators, the ADK
# runtime) will treat ``root_agent`` as the only intended export and
# will flag ``from greeting_agent.agent import *`` accordingly.
__all__ = ["root_agent"]

# =====================================================================
# Module Self-Check (Development Aid)
# =====================================================================

# When this file is executed directly (e.g., ``python -m
# greeting_agent.agent`` or ``python greeting_agent/agent.py``), the
# block below runs a quick sanity check that prints the agent's
# configuration. It is not used by the ADK runtime and has no effect
# when the module is imported normally.
#
# NOTE: Guard with ``__name__ == "__main__"`` so importing the module
# never triggers side effects. This keeps test suites fast and
# predictable, and prevents log spam during routine imports.
#
# The output format is deliberately simple (``key : value`` per line)
# so it can be copy-pasted into bug reports or chat messages without
# reformatting.
if __name__ == "__main__":
    # Print a human-readable summary of the configured agent. This is
    # handy for quick debugging without needing to spin up the full
    # ADK runtime.
    print(f"Agent name        : {root_agent.name}")
    print(f"Agent model       : {root_agent.model}")
    print(f"Agent description : {root_agent.description}")

    # ``!r`` invokes ``repr()`` on the instruction string so embedded
    # newlines and quotes are visible in the output. This is useful
    # for spotting stray whitespace or escaped characters that could
    # change how the model interprets the prompt.
    print(f"Instruction (raw) : {root_agent.instruction!r}")