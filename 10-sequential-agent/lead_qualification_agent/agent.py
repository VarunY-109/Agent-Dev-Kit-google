"""
Lead Qualification Agent Module.

This module defines a sequential agent pipeline for processing sales leads through
three stages: validation, scoring, and action recommendation. The pipeline ensures
leads are processed in a deterministic order, with each sub-agent building upon the
output of the previous one.
"""

from google.adk.agents import SequentialAgent

# Import the three specialized sub-agents that form the qualification pipeline.
from .subagents.recommender import action_recommender_agent
from .subagents.scorer import lead_scorer_agent

from .subagents.validator import lead_validator_agent

# Define the root sequential agent that orchestrates the lead qualification workflow.
# Each sub-agent runs in order, passing its output to the next stage in the pipeline.
root_agent = SequentialAgent(
    name="LeadQualificationPipeline",
    # The pipeline order: validate first, then score, then recommend actions.
    # This order ensures recommendations are based on validated and scored leads.
    sub_agents=[lead_validator_agent, lead_scorer_agent, action_recommender_agent],
    description="A pipeline that validates, scores, and recommends actions for sales leads",
)