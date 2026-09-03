from google.adk.agents import Agent

root_agent = Agent(
    name="code_translator_agent",
    model="gemini-2.0-flash",
    description="Code translator agent",
    instruction="""
    You are an AI agent that translates code between programming languages.
    Given source code and a target language, translate the code while maintaining logic.
    Support translations between Python, JavaScript, Java, C++, and Go.
    Preserve comments and variable naming conventions where possible.
    """,
)
