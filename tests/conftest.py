"""Shared fakes and a test client. No test here calls a real model or needs a key."""
import pytest
from fastapi.testclient import TestClient

from app import main


class FakeGenerator:
    """Stands in for app.generator.OpenRouterGenerator: generate(prompt, seed) -> dict."""

    def __init__(self, fail_on=()):
        self.calls = []
        self.fail_on = set(fail_on)          # prompts containing any of these strings raise

    def generate(self, prompt: str, seed: int) -> dict:
        self.calls.append({"prompt": prompt, "seed": seed})
        if any(s in prompt for s in self.fail_on):
            raise RuntimeError("fake generation failure")
        return {"bytes": PNG_1PX, "media_type": "image/png", "cost": 0.014, "model": "fake/image"}


class FakeCritic:
    """Stands in for app.critic.OpenRouterCritic's model call: ask(model, image, media_type, prompt) -> str.

    Replies are taken from a queue per model, so a test decides exactly what each critic says."""

    def __init__(self, replies=None):
        self.replies = {k: list(v) for k, v in (replies or {}).items()}
        self.calls = []

    def ask(self, model: str, image: bytes, media_type: str, prompt: str) -> str:
        self.calls.append({"model": model, "image": image, "media_type": media_type, "prompt": prompt})
        queue = self.replies.get(model) or self.replies.get("*") or []
        return queue.pop(0) if queue else "no reply"


# A valid 1x1 PNG, so code that reads PNG chunks has a real file to work on.
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc0f01f0005000201c5d6a2a30000000049454e44ae426082")

GOOD_BRIEF = {"product_name": "Handwoven storage basket", "color": "Navy blue", "material": "Seagrass",
              "background": "Plain white", "style": "Minimal, natural light",
              "extra_details": "Has two leather handles"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Default settings for a test: 5 variations, storage in a temp folder, no key."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("VARIATIONS", "5")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "generated"))
    return monkeypatch


@pytest.fixture
def generator():
    return FakeGenerator()


@pytest.fixture
def critic():
    return FakeCritic()


@pytest.fixture
def client(env, generator, critic):
    main.app.dependency_overrides[main.get_generator] = lambda: generator
    main.app.dependency_overrides[main.get_critic] = lambda: critic
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()
