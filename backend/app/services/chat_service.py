"""Bridge the synchronous Groq loop to FastAPI's worker-thread routes."""
def run_agent(history: list, message: str, *, api_key: str | None = None) -> tuple[str, list]:
    from backend.app.agent import agent
    return agent.run(history, message, raise_errors=True, groq_api_key=api_key)
