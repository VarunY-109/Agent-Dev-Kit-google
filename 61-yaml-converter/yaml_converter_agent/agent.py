from google.adk.agents import Agent

root_agent = Agent(
    name="yaml_converter_agent",
    model="gemini-2.0-flash",
    description="YAML converter agent",
    instruction="""
    You are an AI agent that converts between YAML and other formats.
    Given input data, convert between YAML, JSON, and TOML.
    Preserve structure and data types during conversion.
    Validate output format and fix common YAML issues.
    """,
)
