from google.adk.agents import Agent

root_agent = Agent(
    name="code_complexity_agent",
    model="gemini-2.0-flash",
    description="Code complexity analyzer agent",
    instruction="""
    You are an AI agent that analyzes code complexity.
    Given Python code, calculate cyclomatic complexity and maintainability index.
    Identify functions that are too complex and suggest refactoring.
    Provide a complexity report with scores and recommendations.
    """,
)
