from google.adk.agents import Agent

root_agent = Agent(
    name="json_validator_agent",
    model="gemini-2.0-flash",
    description="JSON validator agent",
    instruction="""
    You are an AI agent that validates JSON data.
    Given JSON data and a schema, validate the data structure.
    Check for missing fields, wrong data types, and format issues.
    Provide detailed validation reports with line numbers.
    """,
)
