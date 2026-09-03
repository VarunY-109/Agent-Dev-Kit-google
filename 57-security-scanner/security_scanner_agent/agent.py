from google.adk.agents import Agent

root_agent = Agent(
    name="security_scanner_agent",
    model="gemini-2.0-flash",
    description="Security scanner agent",
    instruction="""
    You are an AI agent that scans code for security vulnerabilities.
    Given Python code, identify potential security issues:
    - SQL injection risks
    - Hardcoded secrets
    - Insecure dependencies
    - XSS vulnerabilities
    Provide severity ratings and fix suggestions.
    """,
)
