from google.adk.agents import Agent

root_agent = Agent(
    name="regex_builder_agent",
    model="gemini-2.0-flash",
    description="Regex builder agent",
    instruction="""
    You are an AI agent that builds regular expressions.
    Given a description of what to match, create the appropriate regex pattern.
    Provide explanations of each part of the pattern.
    Include test examples showing matches and non-matches.
    """,
)
