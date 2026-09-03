from google.adk.agents import Agent

root_agent = Agent(
    name="dependency_checker_agent",
    model="gemini-2.0-flash",
    description="Dependency checker agent",
    instruction="""
    You are an AI agent that checks project dependencies.
    Given a requirements.txt or package.json, identify:
    - Outdated packages
    - Security vulnerabilities
    - Unused dependencies
    - Missing dependencies
    Provide upgrade recommendations.
    """,
)
