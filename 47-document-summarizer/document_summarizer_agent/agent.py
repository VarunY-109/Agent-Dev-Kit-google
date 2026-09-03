from google.adk.agents import Agent

root_agent = Agent(
    name="document_summarizer_agent",
    model="gemini-2.0-flash",
    description="Document summarizer agent",
    instruction="""
    You are an AI agent that summarizes documents.
    Given a document or long text, create a concise summary.
    Extract key points, main arguments, and important conclusions.
    Support multiple summary lengths: short (1-2 sentences), medium (1 paragraph), or detailed (bullet points).
    """,
)
