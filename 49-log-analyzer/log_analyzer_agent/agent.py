from google.adk.agents import Agent

root_agent = Agent(
    name="log_analyzer_agent",
    model="gemini-2.0-flash",
    description="Log analyzer agent",
    instruction="""
    You are an AI agent that analyzes application logs.
    Given log entries, identify patterns, errors, warnings, and anomalies.
    Provide insights on root causes and suggest fixes.
    Support common log formats: JSON, plain text, and syslog.
    """,
)
