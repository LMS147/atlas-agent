"""Backend paths shared by future API services."""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SEED_DIR = BACKEND_DIR / "seed"
