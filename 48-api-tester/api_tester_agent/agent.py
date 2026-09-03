from google.adk.agents import Agent

root_agent = Agent(
    name="api_tester_agent",
    model="gemini-2.0-flash",
    description="API tester agent",
    instruction="""
    You are an AI agent that generates API test cases.
    Given an API endpoint URL, method, and parameters, generate comprehensive test cases.
    Include tests for success scenarios, error handling, edge cases, and authentication.
    Output test code in Python using the requests library.
    """,
)
