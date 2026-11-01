"""ImageCritic: the saved image + the brief's checklist -> a checked critique (spec.md, "Critique").

The image itself goes to the vision model as a base64 data URL in an image content part, next
to the checklist. Each model gets at most two tries for a usable reply. A second model answers
the same checklist; where the two disagree, the result says so. Scores come from
critique_parser, never from the model's text.
"""
import base64

from app.critique_parser import build_checklist, check, disagreements, extract_json

# Hidden reasoning is per model: mimo returns empty content with it on, minimax needs it.
# The SDK's reasoning object only knows "effort" ({"enabled": False} is sent as {}).
REASONING = {"xiaomi/mimo-v2.6-flash": {"effort": "none"}}
MAX_TOKENS = 1500
TRIES = 2

PROMPT = """You are checking a generated product listing image against the seller's brief.
Answer every item below with true or false, strictly from what is visible in the image.
For each item, the evidence must describe what you actually see (for example the actual color).
Also list anything else wrong with the image (extra objects, distorted shapes) under "problems".
Reply with one JSON object and nothing else:
{{"checks": [{{"requirement": "<item text, copied exactly>", "met": true, "evidence": "<what you see>"}}],
 "problems": ["<problem>"]}}

Items:
{items}"""


class OpenRouterCritic:
    """The model call only: one chat request with the image attached."""

    def __init__(self, api_key: str, client=None):
        if client is None:
            from openrouter import OpenRouter
            client = OpenRouter(api_key=api_key)
        self.client = client

    def ask(self, model: str, image: bytes, media_type: str, prompt: str) -> str:
        data = base64.b64encode(image).decode()
        extra = {"reasoning": REASONING[model]} if model in REASONING else {}
        r = self.client.chat.send(model=model, max_tokens=MAX_TOKENS, messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}]}], **extra)
        return r.choices[0].message.content or ""


def critique_image(asker, model: str, image: bytes, media_type: str, requirements: list[str]) -> dict | None:
    """A checked critique from one model, or None if two replies in a row were unusable."""
    prompt = PROMPT.format(items="\n".join(f"- {r}" for r in requirements))
    for _ in range(TRIES):
        result = check(requirements, extract_json(asker.ask(model, image, media_type, prompt)))
        if result["usable"]:
            return result
    return None


def run_critique(asker, settings, image: bytes, media_type: str, brief) -> dict:
    """The /api/critique response: the first critic's checked result and the second critic's disagreements."""
    requirements = build_checklist(brief)
    first = critique_image(asker, settings.critique_model, image, media_type, requirements)
    if first is None:
        return {"status": "unavailable"}
    checked = {k: v for k, v in first.items() if k != "usable"}
    out = {"status": "ok", "model": settings.critique_model, **checked, "disagreements": [],
           "second_model": settings.second_critique_model, "second_status": "off"}
    if settings.second_critique_model:
        second = critique_image(asker, settings.second_critique_model, image, media_type, requirements)
        if second is None:
            out["second_status"] = "unavailable"
        else:
            out["second_status"] = "ok"
            out["disagreements"] = disagreements(first, second)
    return out
