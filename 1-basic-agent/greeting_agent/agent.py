"""Greeting agent module using Google's ADK (Agent Development Kit).

Purpose:
    This module defines a simple conversational agent that interacts with users
    by asking for their name and responding with a personalized greeting.
    It serves as a foundational "Hello, World!"-style example for getting
    started with the Google Agent Development Kit (ADK).

Usage:
    The module is typically imported and executed via the ADK runtime.
    From a project root, you can run the agent locally with:

        adk run 1-basic-agent/greeting_agent

    Alternatively, you can start an API server for the agent with:

        adk api_server 1-basic-agent/greeting_agent

    Once the server is running, requests may be sent to the agent's endpoint
    with a user message such as "Hello!" and the agent will prompt for the
    user's name before replying with a personalized greeting.

Example:
    >>> from greeting_agent.agent import root_agent
    >>> root_agent.name
    'greeting_agent'
    >>> root_agent.model
    'gemini-2.0-flash'

Metadata:
    :author:  ADK Example Authors
    :version: 0.1.0
    :since:   2024
    :license: Apache-2.0
"""

# =====================================================================
# Imports
# =====================================================================

# Google ADK provides the `Agent` base class used to construct
# conversational agents backed by large language models. The Agent
# class wires together a model identifier, instruction prompt, and
# metadata so the ADK runtime can orchestrate turns with the user.
from google.adk.agents import Agent

# =====================================================================
# Agent Definition
# =====================================================================

# Initialize the root agent responsible for greeting users.
#
# NOTE: The `root_agent` name is a conventional identifier expected by
# the ADK runtime. When the module is loaded by `adk run` or
# `adk api_server`, the runtime looks up this attribute to determine
# which agent should handle incoming user requests.
#
# The agent is configured with:
#   * `name`         - A short, machine-friendly identifier used in logs
#                      and tool dispatch.
#   * `model`        - The underlying generative model. Gemini 2.0 Flash
#                      is selected for its low-latency responses, which
#                      makes it well-suited for a conversational greeting
#                      scenario where snappy replies matter more than
#                      deep reasoning.
#   * `description`  - A human-readable summary describing what the
#                      agent does; surfaced in agent listings and UIs.
#   * `instruction`  - The natural-language system prompt that guides
#                      the model's behavior. Here, the agent is told to
#                      (1) ask for the user's name and (2) greet them
#                      using that name.
#
# TODO: Consider extending the instructions to handle edge cases such
# as the user refusing to share their name or providing an empty input.
# FIX: (None) No known issues at this time.
root_agent = Agent(  # type: Agent
    name="greeting_agent",
    model="gemini-2.0-flash",
    description="Greeting agent",
    instruction="""
    You are a helpful assistant that greets the user. 
    Ask for the user's name and greet them by name.
    """,
)

# =====================================================================
# Public API
# =====================================================================

# Expose the configured agent as the module's primary public symbol.
# Importers (including the ADK runtime) should reference `root_agent`
# rather than re-instantiating `Agent` themselves, so that the
# configuration above remains the single source of truth for this
# module's behavior.
__all__ = ["root_agent"]