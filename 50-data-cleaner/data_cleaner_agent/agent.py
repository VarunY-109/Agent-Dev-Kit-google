from google.adk.agents import Agent

root_agent = Agent(
    name="data_cleaner_agent",
    model="gemini-2.0-flash",
    description="Data cleaner agent",
    instruction="""
    You are an AI agent that cleans and transforms data.
    Given messy data, identify and fix issues like:
    - Missing values
    - Duplicate entries
    - Inconsistent formatting
    - Invalid data types
    Output clean data with a report of changes made.
    """,
)
