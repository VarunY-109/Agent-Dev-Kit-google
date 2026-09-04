"""
Lead Qualification Agent - Root Pipeline Module.

This module is the entry point for the sales development agent pipeline. It composes
three specialized sub-agents into a deterministic, sequential workflow that mirrors
how a real-world Sales Development Representative (SDR) triages inbound leads.

Purpose
-------
The root agent defined here is responsible for orchestrating the full lead
qualification lifecycle:

    +-------------------+      +-----------------+      +----------------------+
    |  Lead Validator   | ---> |  Lead Scorer    | ---> |  Action Recommender  |
    +-------------------+      +-----------------+      +----------------------+
     Stage 1: Cleanup,          Stage 2: Numeric        Stage 3: Next-Best-Action
     schema & completeness      priority score          (call, email, nurture,
     checks                      computation             discard, etc.)

Each stage writes structured output into the shared ADK session state, which the
subsequent stage reads. This means the pipeline is *state-coupled*: re-ordering the
sub-agents is a semantic change, not a cosmetic one.

Why a Sequential Pipeline?
-------------------------
We deliberately use ``SequentialAgent`` (instead of ``ParallelAgent`` or a free-form
``Agent`` loop) because:

1. **Validation MUST precede scoring.** You cannot meaningfully score a lead whose
   email is malformed or whose company field is empty.
2. **Scoring MUST precede recommendation.** A recommendation to "call immediately"
   has different urgency depending on whether the lead scored 20 or 90.
3. **Debuggability.** A sequential pipeline produces a clean, replayable trace where
   every intermediate state is inspectable - invaluable when an SDR disputes the
   final recommendation.

Typical Usage
-------------
The module is designed to be auto-discovered by the Google ADK runner:

    # From the project root, run:
    #   adk run lead_qualification_agent
    #
    # Or import it programmatically for unit tests:
    >>> from lead_qualification_agent.agent import root_agent
    >>> root_agent.name
    'LeadQualificationPipeline'
    >>> [a.name for a in root_agent.sub_agents]
    ['LeadValidator', 'LeadScorer', 'ActionRecommender']

Module Layout
-------------
::

    lead_qualification_agent/
    ├── __init__.py
    ├── agent.py                  <-- THIS FILE (root composition)
    └── subagents/
        ├── validator/
        │   └── lead_validator_agent.py
        ├── scorer/
        │   └── lead_scorer_agent.py
        └── recommender/
            └── action_recommender_agent.py

Notes
 -----
    - This is version 1.2.0 - it is the production-tracked version consumed by the
      sales automation orchestrator service.
    - BREAKING CHANGE from 1.0.x -> 1.1.0: the recommender now reads the validated
      lead's normalized field names; do not bypass the validator in tests.
    - BREAKING CHANGE from 1.1.x -> 1.2.0: ``description`` string was rewritten to
      align with the public docs team guidelines.

Metadata
--------
:author:  Sales Automation Team <sales-automation@example.com>
:version: 1.2.0
:date:    2025-01-15
:license: Proprietary - Internal use only.
:maintainer: Jordan Lee
:see_also:
    - `google.adk.agents.SequentialAgent` documentation.
    - Module ``subagents.validator`` for Stage 1 details.
    - Module ``subagents.scorer`` for Stage 2 details.
    - Module ``subagents.recommender`` for Stage 3 details.

TODO
----
- Add a `version` field to ``root_agent`` config once ADK supports it natively.
- Consider exposing a `pipeline_summary()` helper for the ops dashboard.
"""

# === IMPORTS ==================================================================

# Third-party ADK import. SequentialAgent is the orchestrator primitive that
# guarantees ordered, single-threaded execution of sub-agents and provides
# automatic shared session state propagation.
#
# type: GoogleADKModule
from google.adk.agents import SequentialAgent  # type: SequentialAgent

# Import the three specialized sub-agents that form the qualification pipeline.
# NOTE: We import `recommender` first and `validator` last purely for cosmetic
# reasons in this file (alphabetical grouping of the imports); the actual
# *execution order* is dictated by the `sub_agents` list passed to
# SequentialAgent below - NOT by import order.
#
# Each sub-agent is itself an `LlmAgent` (or `BaseAgent`) instance defined in
# its own module to keep responsibilities isolated and individually mockable
# in unit tests.
from .subagents.recommender import action_recommender_agent  # type: action_recommender_agent
from .subagents.scorer import lead_scorer_agent               # type: lead_scorer_agent
from .subagents.validator import lead_validator_agent         # type: lead_validator_agent

# === CONSTANTS ================================================================

#: Human-readable name of the root pipeline. Used in logs, traces, and the ADK UI.
#: Changing it would break dashboards that grep on this string, so it is treated
#: as effectively immutable per the team's stability contract.
PIPELINE_NAME = "LeadQualificationPipeline"

#: Short description displayed in the ADK web runner and CLI tooling.
#: Kept under 100 characters to render cleanly in the sidebar.
#: NOTE: Keep this in sync with the public docs at
#: https://internal.example.com/docs/sales-agents/lead-qualification
PIPELINE_DESCRIPTION = (
    "A pipeline that validates, scores, and recommends actions for sales leads"
)

#: The canonical, immutable pipeline order. Declared as a tuple so accidental
#: mutation at runtime raises a clear ``TypeError`` rather than silently changing
#: business behavior.
#:
#: IMPORTANT: This tuple is the single source of truth for stage ordering. Tests
#: assert against this constant - do NOT inline the list literal elsewhere.
PIPELINE_ORDER = (
    "validator",   # Stage 1: data quality gate
    "scorer",      # Stage 2: priority scoring
    "recommender", # Stage 3: next-best-action decision
)

# === AGENT CONFIGURATION =====================================================

# Define the root sequential agent that orchestrates the lead qualification workflow.
# Each sub-agent runs in order, passing its output to the next stage in the pipeline.
#
# The SequentialAgent class guarantees:
#   * Strict ordering (no parallel execution)
#   * Shared session state across all sub-agents
#   * Automatic short-circuiting if a sub-agent raises an unrecoverable error
#
# Return type: google.adk.agents.SequentialAgent
root_agent = SequentialAgent(
    # The human-readable identifier used in logs, traces, and the ADK web UI.
    # type: str
    name=PIPELINE_NAME,

    # The pipeline order: validate first, then score, then recommend actions.
    # This order ensures recommendations are based on validated and scored leads.
    #
    # IMPORTANT: Re-ordering this list will silently change business outcomes,
    # because later stages may assume the presence of keys written by earlier ones
    # (e.g., `lead.score` is required by the recommender, and `lead.normalized`
    # is required by the scorer). The unit tests assert the exact ordering.
    #
    # type: list[BaseAgent]
    sub_agents=[
        lead_validator_agent,        # Stage 1: data quality gate
        lead_scorer_agent,           # Stage 2: priority scoring
        action_recommender_agent,    # Stage 3: next-best-action decision
    ],

    # A short, single-sentence description used by the ADK UI and tooling.
    # TODO: Expand this description once the team finalizes the public-facing docs.
    # type: str
    description=PIPELINE_DESCRIPTION,
)

# === SANITY ASSERTIONS ========================================================

# Defensive assertions that fail loudly during import if the pipeline is
# misconfigured. These run exactly once at module load time, so they have no
# runtime overhead during normal agent execution but catch developer mistakes
# (e.g., accidentally removing a sub-agent) before the pipeline is ever invoked.
#
# NOTE: We use plain ``assert`` rather than ``if/raise`` so these checks are
# stripped automatically in optimized (``python -O``) production builds.
assert len(root_agent.sub_agents) == 3, (
    f"Pipeline must contain exactly 3 stages; found {len(root_agent.sub_agents)}. "
    f"Did someone remove a sub-agent?"
)
assert root_agent.sub_agents[0].name == "LeadValidator", (
    "First pipeline stage must be the LeadValidator. Re-ordering sub_agents "
    "is a semantic change; please update PIPELINE_ORDER and the team docs."
)
assert root_agent.sub_agents[2].name == "ActionRecommender", (
    "Last pipeline stage must be the ActionRecommender."
)

# === PUBLIC EXPORTS ===========================================================

# Expose the configured agent under the conventional ``root_agent`` name so the
# ADK CLI (``adk run ...``) and the web runner can auto-discover it. This is
# the *only* public symbol of this module - everything else is an implementation
# detail.
__all__ = ["root_agent", "PIPELINE_NAME", "PIPELINE_DESCRIPTION", "PIPELINE_ORDER"]

# === SMOKE TEST ENTRY POINT ===================================================

# Provide a quick smoke-test entry point: running this module directly will
# print the pipeline structure without executing any sub-agents.
#
# Usage:
#     python -m lead_qualification_agent.agent
#
# This is useful for CI sanity checks and for onboarding new engineers who want
# to confirm their checkout is wired up correctly without standing up the ADK
# runner.
if __name__ == "__main__":
    # type: () -> None
    # Header banner for human readability when running from a terminal.
    print(f"=== {PIPELINE_NAME} ===")
    print(f"Description: {PIPELINE_DESCRIPTION}")
    print(f"Stages ({len(root_agent.sub_agents)}):")
    # Iterate with a 1-based index so the printed output matches how SDRs
    # refer to the pipeline stages in conversation ("Stage 2 gave it a 78").
    for index, agent in enumerate(root_agent.sub_agents, start=1):
        # type: (int, SequentialAgent) -> None
        # NOTE: We swallow the description to ``str(...)`` in case it is ever
        # upgraded to a richer object (e.g., a Pydantic model).
        print(f"  {index}. {agent.name} - {getattr(agent, 'description', '(no description)')}")
    print("=== Smoke test complete (no sub-agents executed) ===")