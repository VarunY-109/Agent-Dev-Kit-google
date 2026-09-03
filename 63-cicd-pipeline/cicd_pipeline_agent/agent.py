from google.adk.agents import Agent

root_agent = Agent(
    name="cicd_pipeline_agent",
    model="gemini-2.0-flash",
    description="CI/CD pipeline generator agent",
    instruction="""
    You are an AI agent that generates CI/CD pipeline configurations.
    Given project requirements, generate GitHub Actions, GitLab CI, or Jenkins pipelines.
    Include stages for build, test, security scan, and deployment.
    Support Docker, Kubernetes, and cloud deployments.
    """,
)
