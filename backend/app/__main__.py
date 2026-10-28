"""Configuration-aware API launcher used by Termux and local development."""
import uvicorn
from backend.app.config import load_settings


def main():
    settings = load_settings()
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, workers=1)

if __name__ == "__main__":
    main()
