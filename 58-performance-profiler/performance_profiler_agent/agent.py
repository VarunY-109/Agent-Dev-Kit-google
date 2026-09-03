from google.adk.agents import Agent

root_agent = Agent(
    name="performance_profiler_agent",
    model="gemini-2.0-flash",
    description="Performance profiler agent",
    instruction="""
    You are an AI agent that profiles code performance.
    Given Python code, identify performance bottlenecks:
    - N+1 query problems
    - Unnecessary loops
    - Memory leaks
    - CPU-intensive operations
    Suggest optimizations with code examples.
    """,
)
