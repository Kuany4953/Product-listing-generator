"""ImageGenerator: prompt + seed -> image bytes, through OpenRouter's Image API (spec.md, "Generation").

One call per image, no retries in our code, a 90-second timeout. The SDK is imported only
when a real client is built, so tests that pass a fake client never need it or a key.
"""
import base64

TIMEOUT_MS = 90_000


class OpenRouterGenerator:
    def __init__(self, api_key: str, model: str, aspect_ratio: str, client=None):
        if client is None:
            from openrouter import OpenRouter
            client = OpenRouter(api_key=api_key)
        self.client = client
        self.model = model
        self.aspect_ratio = aspect_ratio

    def generate(self, prompt: str, seed: int) -> dict:
        """Bytes, media type, cost from the reply's usage, and the model that made it."""
        r = self.client.images.generate(model=self.model, prompt=prompt, seed=seed,
                                        aspect_ratio=self.aspect_ratio, timeout_ms=TIMEOUT_MS)
        item = r.data[0]
        return {"bytes": base64.b64decode(item.b64_json), "media_type": item.media_type,
                "cost": getattr(r.usage, "cost", None), "model": self.model}
