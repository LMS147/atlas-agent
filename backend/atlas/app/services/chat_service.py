"""Groq adapters for ordinary and streamed requests."""
def run_agent(history, message, *, api_key=None):
    from backend.atlas.app.agent import agent
    return agent.run(history, message, raise_errors=True, groq_api_key=api_key)

def run_agent_stream(history, message, emit, *, api_key=None):
    from backend.atlas.app.agent import agent
    return agent.run(history, message, raise_errors=True, groq_api_key=api_key, on_event=emit)
