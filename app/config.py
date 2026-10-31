"""Settings from environment variables (spec.md, "Configuration"). A local .env is loaded in development.

Read on every call, not cached, so tests can change the environment between requests.
The API key is read here and nowhere else; it is never written to a file or sent to the page.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()          # .env is git-ignored; existing environment variables win

MAX_VARIATIONS = 5     # prompts.py has exactly five compositions


@dataclass(frozen=True)
class Settings:
    variations: int
    image_model: str
    image_aspect_ratio: str
    critique_model: str
    second_critique_model: str | None
    storage_dir: Path
    api_key: str | None


def get_settings() -> Settings:
    try:
        variations = int(os.environ.get("VARIATIONS", "5"))
    except ValueError:
        raise ValueError("VARIATIONS must be a whole number from 1 to 5") from None
    if not 1 <= variations <= MAX_VARIATIONS:
        raise ValueError("VARIATIONS must be a whole number from 1 to 5")
    second = os.environ.get("SECOND_CRITIQUE_MODEL", "xiaomi/mimo-v2.6-flash").strip()
    return Settings(
        variations=variations,
        image_model=os.environ.get("IMAGE_MODEL", "black-forest-labs/flux.2-klein-4b"),
        image_aspect_ratio=os.environ.get("IMAGE_ASPECT_RATIO", "1:1"),
        critique_model=os.environ.get("CRITIQUE_MODEL", "minimax/minimax-m3"),
        second_critique_model=second or None,
        storage_dir=Path(os.environ.get("STORAGE_DIR", "./generated")),
        api_key=os.environ.get("OPENROUTER_API_KEY") or None,
    )
