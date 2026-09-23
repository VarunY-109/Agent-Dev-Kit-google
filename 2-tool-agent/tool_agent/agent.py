# === MODULE METADATA ===
# Module: tool_agent/agent.py
# Purpose: Defines and configures the root agent for the Tool Agent application.
#          This agent leverages Google ADK (Agent Development Kit) and is equipped
#          with web search capabilities to assist users in retrieving real-time
#          information from the internet.
# Author: Tool Agent Development Team
# Date: 2025-01-01
# Version: 1.0.0
# License: See project LICENSE file for details.
#
# USAGE EXAMPLE:
#   from tool_agent.agent import root_agent
#   # Use root_agent with ADK session runners or deployment configs
#
# DEPENDENCIES:
#   - google.adk.agents: Provides the Agent base class and agent lifecycle management.
#   - google.adk.tools: Provides tool integrations including google_search.
#
# CHANGELOG:
#   v1.0.0 (2025-01-01): Initial agent configuration with google_search tool.
#
# === END METADATA ===


# === IMPORTS ===
# Import the Agent class from Google ADK, which serves as the core building block
# for defining conversational agents with tools, models, and instructions.
from google.adk.agents import Agent
# Import the google_search tool, which enables the agent to perform real-time
# web searches and retrieve information from across the internet.
from google.adk.tools import google_search


# === AGENT CONFIGURATION ===
# TODO: Consider adding a configurable model selection mechanism (e.g., environment
# variable or config file) to allow swapping between gemini-2.0-flash and other
# Gemini models based on use case or cost constraints.
#
# NOTE: The model "gemini-2.0-flash" is selected for its balance of speed and
# intelligence. For more complex reasoning tasks, consider upgrading to
# gemini-2.0-pro or a later model version.
#
# FIXME: The description "Tool agent" is generic. Consider making it more
# descriptive (e.g., "A search-enabled assistant agent") for better clarity
# in multi-agent orchestration scenarios.

# type: (name: str, model: str, description: str, instruction: str, tools: list) -> Agent
root_agent = Agent(
    # The unique identifier for this agent within the ADK framework.
    # This name is used internally for routing, logging, and debugging purposes.
    # It should be unique within the scope of a multi-agent application.
    name="tool_agent",

    # The AI model to be used for inference. This determines the capabilities,
    # latency, and cost profile of the agent's responses.
    # Supported models depend on the Google ADK version and available endpoints.
    model="gemini-2.0-flash",

    # A brief, human-readable description of the agent's role and purpose.
    # This is primarily used for documentation, monitoring dashboards, and
    # orchestration layer routing decisions.
    description="Tool agent",

    # The system-level instruction prompt that defines the agent's behavior,
    # personality, and tool usage guidelines. This prompt is prepended to every
    # conversation turn to maintain consistent agent behavior.
    #
    # NOTE: Keep instructions concise but comprehensive. Ambiguous instructions
    # may lead to unexpected tool usage or response patterns.
    instruction="""
    You are a helpful assistant that can use the following tools:
    - google_search
    """,

    # The list of tools available to the agent. Tools extend the agent's
    # capabilities beyond text generation, enabling actions like web search,
    # database queries, API calls, etc.
    #
    # TODO: Evaluate whether additional tools (e.g., calculator, code execution,
    # file I/O) should be added to enhance the agent's utility.
    tools=[google_search],
)


# === AGENT DEPLOYMENT NOTES ===
#
# This root_agent instance is intended to be the entry point for the ADK
# application. It should be passed to a SessionService or Runner for execution.
#
# EXAMPLE DEPLOYMENT:
#   from google.adk.sessions import InMemorySessionService
#   from google.adk.runner import Runner
#
#   session_service = InMemorySessionService()
#   runner = Runner(agent=root_agent, session_service=session_service)
#
# PERFORMANCE CONSIDERATIONS:
# - The google_search tool introduces network latency. Consider implementing
#   caching or rate limiting if this agent handles high-throughput requests.
# - Model selection (gemini-2.0-flash) balances cost and quality, but monitor
#   token usage in production environments.
#
# SECURITY CONSIDERATIONS:
# - Ensure that the google_search tool does not expose sensitive query data
#   in logs or monitoring systems.
# - Validate and sanitize any user inputs before they reach the agent to
#   prevent prompt injection attacks.
#
# === END CONFIGURATION ===