"""OpenRouterGenerator with a fake SDK client: the request it makes and what it returns. No key, no call."""
import base64
from types import SimpleNamespace

from app.generator import OpenRouterGenerator
from tests.conftest import PNG_1PX


class FakeImages:
    def __init__(self):
        self.kwargs = None

    def generate(self, **kwargs):
        self.kwargs = kwargs
        item = SimpleNamespace(b64_json=base64.b64encode(PNG_1PX).decode(), media_type="image/png")
        return SimpleNamespace(data=[item], usage=SimpleNamespace(cost=0.014))


def test_one_image_api_call_with_model_seed_aspect_and_timeout():
    fake = SimpleNamespace(images=FakeImages())
    g = OpenRouterGenerator(api_key="unused", model="black-forest-labs/flux.2-klein-4b", aspect_ratio="1:1",
                            client=fake)
    out = g.generate("a prompt", 4150)
    assert fake.images.kwargs == {"model": "black-forest-labs/flux.2-klein-4b", "prompt": "a prompt",
                                  "seed": 4150, "aspect_ratio": "1:1", "timeout_ms": 90_000}
    assert out == {"bytes": PNG_1PX, "media_type": "image/png", "cost": 0.014,
                   "model": "black-forest-labs/flux.2-klein-4b"}
