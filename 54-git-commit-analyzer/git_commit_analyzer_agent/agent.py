from google.adk.agents import Agent

root_agent = Agent(
    name="git_commit_analyzer_agent",
    model="gemini-2.0-flash",
    description="Git commit analyzer agent",
    instruction="""
    You are an AI agent that analyzes git commit messages.
    Given a commit message, determine if it follows conventional commit standards.
    Suggest improvements for clarity, brevity, and convention compliance.
    Categorize commits as feat, fix, docs, style, refactor, test, or chore.
    """,
)
