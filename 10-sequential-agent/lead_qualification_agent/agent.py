"""
Lead Qualification Agent Module.

This module defines the root sequential agent that orchestrates the lead qualification
workflow used by the sales automation system. The agent is composed of three specialized
sub-agents arranged in a strict pipeline order:

    1. Lead Validator    - Sanitizes input, checks required fields, and verifies
                            that the lead meets minimum data quality standards.
    2. Lead Scorer       - Computes a numeric priority score based on demographic,
                            behavioral, and firmographic signals.
    3. Action Recommender - Suggests the next-best-action (e.g., call, email,
                            nurture, discard) based on the validated + scored lead.

The pipeline is deterministic: every sub-agent MUST complete before the next one
starts, and the output of each stage is appended to the shared session state so the
next stage can consume it. This design mirrors a real-world SDR (Sales Development
Representative) workflow where you would never score an invalid lead, nor recommend
actions on a lead that has not been scored.

Typical usage
-------------
The agent is usually launched through the Google ADK runner, but it can also be
imported directly for unit tests:

    >>> from lead_qualification_agent.agent import root_agent
    >>> root_agent.name
    'LeadQualificationPipeline'
    >>> [a.name for a in root_agent.sub_agents]
    ['LeadValidator', 'LeadScorer', 'ActionRecommender']

Metadata
--------
:author:  Sales Automation Team
:version: 1.2.0
:date:    2025-01-15
:license: Proprietary
:see_also:
    - google.adk.agents.SequentialAgent
    - .subagents.validator.lead_validator_agent
    - .subagents.scorer.lead_scorer_agent
    - .subagents.recommender.action_recommender_agent
"""

# === IMPORTS ==================================================================

from google.adk.agents import SequentialAgent  # type: SequentialAgent

# Import the three specialized sub-agents that form the qualification pipeline.
# NOTE: We import the validator last only because of Python's import resolution;
# it has no effect on runtime ordering. The pipeline order is enforced by the
# `sub_agents` list below, not by import order.
from .subagents.recommender import action_recommender_agent
from .subagents.scorer import lead_scorer_agent
from .subagents.validator import lead_validator_agent

# === AGENT CONFIGURATION =====================================================

# Define the root sequential agent that orchestrates the lead qualification workflow.
# Each sub-agent runs in order, passing its output to the next stage in the pipeline.
# The SequentialAgent class guarantees:
#   * Strict ordering (no parallel execution)
#   * Shared session state across all sub-agents
#   * Automatic short-circuiting if a sub-agent raises an unrecoverable error
root_agent = SequentialAgent(
    # The human-readable identifier used in logs, traces, and the ADK web UI.
    name="LeadQualificationPipeline",

    # The pipeline order: validate first, then score, then recommend actions.
    # This order ensures recommendations are based on validated and scored leads.
    # IMPORTANT: Re-ordering this list will silently change business outcomes,
    # because later stages may assume the presence of keys written by earlier ones
    # (e.g., `lead.score` is required by the recommender).
    sub_agents=[
        lead_validator_agent,        # Stage 1: data quality gate
        lead_scorer_agent,           # Stage 2: priority scoring
        action_recommender_agent,    # Stage 3: next-best-action decision
    ],

    # A short, single-sentence description used by the ADK UI and tooling.
    # TODO: Expand this description once the team finalizes the public-facing docs.
    description=(
        "A pipeline that validates, scores, and recommends actions for sales leads"
    ),
)

# === METADATA & EXPORTS ======================================================

# Expose the configured agent under the conventional `root_agent` name so the
# ADK CLI (`adk run ...`) and the web runner can auto-discover it.
__all__ = ["root_agent"]

# Provide a quick smoke-test entry point: running this module directly will
# print the pipeline structure without executing any sub-agents.
if __name__ == "__main__":
    # type: () -> None
    print(f"Root agent: {root_agent.name}")
    print(f"Stages ({len(root_agent.sub_agents)}):")
    for index, agent in enumerate(root_agent.sub_agents, start=1):
        # type: (int, SequentialAgent) -> None
        print(f"  {index}. {agent.name} - {agent.description}")