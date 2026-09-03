from google.adk.agents import Agent

root_agent = Agent(
    name="api_mock_generator_agent",
    model="gemini-2.0-flash",
    description="API mock generator agent",
    instruction="""
    You are an AI agent that generates mock API responses.
    Given an API schema or example, generate realistic mock data.
    Support JSON, XML, and CSV formats.
    Include various scenarios: success, error, empty, and edge cases.
    """,
)
