"""
Action Recommender Agent Module
================================

This module defines the **Action Recommender Agent**, a specialized component within
the Lead Qualification pipeline. This agent operates as the final decision-making
node in a sequential agent workflow, taking validated and scored lead data as input
and producing actionable recommendations for the sales team.

Module Purpose
--------------
The Action Recommender Agent is responsible for translating quantitative lead scores
and validation outcomes into qualitative, human-readable action plans that sales
representatives can execute. It acts as the bridge between automated lead scoring
and human-driven sales activities.

Architecture Context
--------------------
In the broader lead qualification system, this agent is the terminal node of a
sequential pipeline:

    1. Lead Validation Agent -> validates lead information
    2. Lead Scoring Agent    -> assigns numerical quality score
    3. Action Recommender    -> THIS MODULE - suggests next steps

Each agent in this sequence passes its output via session state placeholders, which
this agent consumes through its prompt template variables.

State Dependencies
------------------
This agent expects the following session state keys to be populated by upstream agents:
    - ``lead_score``: An integer (typically 1-10) representing lead quality.
    - ``validation_status``: A boolean or string indicating whether the lead passed
      initial validation checks.

Output
------
The agent writes its recommendation to the ``action_recommendation`` session state
key, which downstream consumers (e.g., CRM integrations, notification systems) can
read to trigger subsequent actions.

Scoring Tiers and Recommended Actions
--------------------------------------
The agent's instruction template encodes the following business logic:

    * Invalid leads  -> Request additional/missing information
    * Score 1-3      -> Nurturing actions (educational content, drip campaigns)
    * Score 4-7      -> Qualifying actions (discovery calls, needs assessments)
    * Score 8-10     -> Sales actions (demos, proposals, closing attempts)

Example Usage
-------------
This module is typically not invoked directly. Instead, it is imported and registered
as part of a SequentialAgent pipeline::

    from google.adk.agents import SequentialAgent
    from lead_qualification_agent.subagents.recommender.agent import action_recommender_agent

    pipeline = SequentialAgent(
        name="LeadQualificationPipeline",
        sub_agents=[validation_agent, scoring_agent, action_recommender_agent],
    )

Metadata
--------
:author: Lead Qualification Team
:version: 1.0.0
:date: 2026-01-15
:since: 1.0.0
:see_also: :mod:`lead_qualification_agent.subagents.validation`,
            :mod:`lead_qualification_agent.subagents.scoring`
"""

# =============================================================================
# IMPORTS
# =============================================================================

from google.adk.agents import LlmAgent  # Google's Agent Development Kit LLM agent

# =============================================================================
# CONSTANTS
# =============================================================================

#: The Gemini model identifier used for this agent.
#:
#: Uses ``gemini-2.0-flash`` which provides a strong balance between response
#: quality and latency, making it well-suited for real-time recommendation
#: generation in conversational sales workflows.
#:
#: :type: str
GEMINI_MODEL = "gemini-2.0-flash"

# =============================================================================
# AGENT DEFINITION
# =============================================================================

# NOTE: The instruction template below uses Python format-string syntax with
# curly-brace placeholders (e.g., ``{lead_score}``). The ADK runtime replaces
# these placeholders with values from the session state at invocation time.

# TODO: Consider parameterizing the score thresholds (1-3, 4-7, 8-10) via
# configuration rather than hardcoding them in the instruction string. This would
# allow non-technical users to tune the recommendation tiers without code changes.

# FIXME: The instruction currently has a trailing whitespace issue ("team.    ")
# on the closing line that may cause minor tokenization inconsistencies.
# Cleanup scheduled for v1.0.1.

action_recommender_agent = LlmAgent(
    # type: (str) -> LlmAgent
    name="ActionRecommenderAgent",
    """
    The unique identifier for this agent within the parent SequentialAgent.
    
    This name is used for logging, tracing, and as a reference key when other
    agents need to invoke this agent or read its output. It must be unique
    across all agents in the parent pipeline.
    
    :param name: Must be a valid Python identifier and unique within scope.
    """
    model=GEMINI_MODEL,
    """
    The underlying LLM model used for generating recommendations.
    
    Currently configured to use Gemini 2.0 Flash for its optimal balance of
    speed and reasoning capability. This can be overridden by passing a different
    model identifier if deployment requirements change.
    
    :param model: A valid Gemini model identifier string.
    """
    instruction="""You are an Action Recommendation AI.
    
    Based on the lead information and scoring:
    
    - For invalid leads: Suggest what additional information is needed
    - For leads scored 1-3: Suggest nurturing actions (educational content, etc.)
    - For leads scored 4-7: Suggest qualifying actions (discovery call, needs assessment)
    - For leads scored 8-10: Suggest sales actions (demo, proposal, etc.)
    
    Format your response as a complete recommendation to the sales team.
    
    Lead Score:
    {lead_score}

    Lead Validation Status:
    {validation_status}
    """,
    """
    The system prompt guiding the agent's behavior.
    
    This prompt performs several critical functions:
    
    1. **Role assignment**: Establishes the agent as an "Action Recommendation AI"
       to anchor its persona and response style.
    2. **Decision logic**: Provides explicit branching rules tied to lead score
       ranges and validation status.
    3. **Output formatting**: Directs the agent to produce a complete, ready-to-send
       recommendation suitable for direct consumption by sales personnel.
    4. **Template variables**: Embeds ``{lead_score}`` and ``{validation_status}``
       placeholders that the ADK runtime substitutes from session state.
    
    Score Tier Reference:
        * 1-3  (Low)      -> Educational/nurturing content
        * 4-7  (Medium)   -> Discovery and qualification engagement
        * 8-10 (High)     -> Active sales conversion activities
        * Invalid         -> Information collection and re-engagement
    
    :param instruction: Multi-line prompt with embedded state placeholders.
    """
    description="Recommends next actions based on lead qualification.",
    """
    A brief human-readable summary of this agent's responsibility.
    
    Used by ADK tooling, observability dashboards, and developer documentation
    to describe the agent at a glance without inspecting its full instruction.
    
    :param description: Short, single-sentence purpose statement.
    """
    output_key="action_recommendation",
    """
    The session state key under which this agent's output will be stored.
    
    After the agent generates its recommendation, the resulting text is written
    to ``session.state["action_recommendation"]``. Downstream consumers—such as
    notification services, CRM integrations, or human-facing dashboards—can
    retrieve the result by reading this key.
    
    Naming convention: keys are lowercase with underscores, matching the style
    used by upstream agents (``lead_score``, ``validation_status``) for
    consistency across the pipeline.
    
    :param output_key: Unique key within the session state namespace.
    """
)

# =============================================================================
# MODULE-LEVEL GUARD
# =============================================================================

if __name__ == "__main__":
    # This block executes only when the module is run directly (e.g., for testing).
    # It allows developers to verify the agent definition is syntactically valid
    # and inspect the resulting configuration without spinning up a full workflow.
    # type: () -> None
    print(f"Action Recommender Agent: {action_recommender_agent.name}")
    print(f"Model: {action_recommender_agent.model}")
    print(f"Output Key: {action_recommender_agent.output_key}")