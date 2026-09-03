from google.adk.agents import Agent

root_agent = Agent(
    name="k8s_manifest_agent",
    model="gemini-2.0-flash",
    description="Kubernetes manifest generator agent",
    instruction="""
    You are an AI agent that generates Kubernetes manifests.
    Given application requirements, generate YAML manifests for:
    - Deployments
    - Services
    - ConfigMaps
    - Secrets
    - Ingress rules
    Include resource limits and health checks.
    """,
)
