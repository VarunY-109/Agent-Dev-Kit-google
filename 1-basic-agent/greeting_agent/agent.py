"""Greeting agent module using Google's ADK (Agent Development Kit).

This module defines a simple conversational agent that interacts with users
by asking for their name and responding with a personalized greeting.
"""

from google.adk.agents import Agent

# Initialize the root agent responsible for greeting users.
# The agent uses the Gemini 2.0 Flash model and follows instructions
# to ask for the user's name and respond with a personalized greeting.
root_agent = Agent(
    name="greeting_agent",
    model="gemini-2.0-flash",
    description="Greeting agent",
    instruction="""
    You are a helpful assistant that greets the user. 
    Ask for the user's name and greet them by name.
    """,
)