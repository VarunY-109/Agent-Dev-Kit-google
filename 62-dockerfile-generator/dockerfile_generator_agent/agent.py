from google.adk.agents import Agent

root_agent = Agent(
    name="dockerfile_generator_agent",
    model="gemini-2.0-flash",
    description="Dockerfile generator agent",
    instruction="""
    You are an AI agent that generates Dockerfiles.
    Given a project description or existing code, generate an optimized Dockerfile.
    Include multi-stage builds, security best practices, and layer caching.
    Support Python, Node.js, Go, and Java projects.
    """,
)
