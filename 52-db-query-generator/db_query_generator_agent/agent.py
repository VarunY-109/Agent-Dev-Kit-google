from google.adk.agents import Agent

root_agent = Agent(
    name="db_query_generator_agent",
    model="gemini-2.0-flash",
    description="Database query generator agent",
    instruction="""
    You are an AI agent that generates database queries.
    Given a natural language description, generate SQL queries.
    Support SELECT, INSERT, UPDATE, DELETE, JOIN, and aggregation operations.
    Include explanations of the query logic.
    """,
)
