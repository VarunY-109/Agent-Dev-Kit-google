from google.adk.agents import Agent

root_agent = Agent(
    name="unit_test_generator_agent",
    model="gemini-2.0-flash",
    description="Unit test generator agent",
    instruction="""
    You are an AI agent that generates unit tests.
    Given Python code, generate comprehensive unit tests using pytest.
    Cover happy paths, edge cases, error conditions, and boundary values.
    Include test fixtures and mock objects where needed.
    """,
)
