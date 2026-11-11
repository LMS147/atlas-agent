"""API configuration. Environment variables override backend/.env."""
from dataclasses import dataclass, field
import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
SEED_DIR = BACKEND_DIR / "atlas" / "seed"

@dataclass(frozen=True)
class Settings:
    api_token: str = field(repr=False)
    groq_api_key: str = field(repr=False)
    data_dir: Path = Path("./data")
    host: str = "127.0.0.1"
    port: int = 8000

    def __post_init__(self):
        if len(self.api_token) < 32 or not self.api_token.isascii() or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in self.api_token):
            raise ValueError("ATLAS_API_TOKEN must contain at least 32 printable ASCII characters without whitespace")
        if not self.groq_api_key.strip():
            raise ValueError("GROQ_API_KEY must be configured on the server")
        if not 1 <= self.port <= 65535:
            raise ValueError("ATLAS_PORT must be between 1 and 65535")


def load_settings() -> Settings:
    load_dotenv(BACKEND_DIR / ".env", override=False)
    return Settings(
        api_token=os.getenv("ATLAS_API_TOKEN", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        data_dir=Path(os.getenv("DATA_DIR", "./data")).expanduser().resolve(),
        host=os.getenv("ATLAS_HOST", "127.0.0.1"),
        port=int(os.getenv("ATLAS_PORT", "8000")),
    )
