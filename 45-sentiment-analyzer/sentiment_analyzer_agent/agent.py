from google.adk.agents import Agent

root_agent = Agent(
    name="sentiment_analyzer_agent",
    model="gemini-2.0-flash",
    description="Sentiment analyzer agent",
    instruction="""
    You are an AI agent that analyzes the sentiment of text.
    Given any text input, determine if the sentiment is positive, negative, or neutral.
    Provide a confidence score between 0 and 1.
    Return the result as a JSON object with 'sentiment' and 'confidence' fields.
    """,
)
