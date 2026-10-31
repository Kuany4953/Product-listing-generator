"""FastAPI app and routes (spec.md, "API endpoints").

The generator and critic are FastAPI dependencies, so tests replace them with fakes and
never call a model. Routes that call a model are plain `def`, so FastAPI runs them in its
thread pool and five generations at once do not block each other.
"""
import logging
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import store
from app.brief import GenerateRequest
from app.config import get_settings
from app.generator import OpenRouterGenerator
from app.prompts import build_prompt
from app.screener import screen

log = logging.getLogger(__name__)

app = FastAPI(title="Product Listing Image Generator")


@app.exception_handler(RequestValidationError)
def bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
    """A brief that breaks the rules is a 400 (spec), not FastAPI's default 422 (kept for screening)."""
    fields = sorted({".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()})
    return JSONResponse(status_code=400, content={"detail": f"Check these fields: {', '.join(fields)}"})


def get_generator() -> OpenRouterGenerator | None:
    """The image generator, or None when no key is set (the route then answers 503)."""
    s = get_settings()
    if not s.api_key:
        return None
    return OpenRouterGenerator(api_key=s.api_key, model=s.image_model, aspect_ratio=s.image_aspect_ratio)


def get_critic():
    """The critic's model call. Wired to OpenRouter in week06-sidally."""
    return None


# ---- config (Kuany) ----
@app.get("/api/config")
def config() -> dict:
    return {"variations": get_settings().variations}


# ---- generate (Kuany: validation and screening; Jeevan: generation) ----
@app.post("/api/generate")
def generate(req: GenerateRequest, generator: Annotated[object, Depends(get_generator)]) -> dict:
    settings = get_settings()
    if not 1 <= req.variation <= settings.variations:
        raise HTTPException(400, f"variation must be from 1 to {settings.variations}")
    rejection = screen(req.brief)
    if rejection:
        raise HTTPException(422, rejection)
    if generator is None:
        raise HTTPException(503, "Image generation needs OPENROUTER_API_KEY in the environment.")
    prompt = build_prompt(req.brief, req.variation)
    seed = random.randrange(2**31)
    try:
        image = generator.generate(prompt, seed)
    except Exception as exc:                       # API error, timeout, safety refusal: one slot fails
        log.warning("generation failed for variation %s: %s", req.variation, type(exc).__name__)
        raise HTTPException(502, "Image could not be generated") from None
    record = {"brief": req.brief.model_dump(), "variation": req.variation, "prompt": prompt, "seed": seed,
              "model": image["model"], "media_type": image["media_type"], "cost": image["cost"],
              "created": datetime.now(UTC).isoformat(timespec="seconds")}
    image_id = store.save(settings.storage_dir, image["bytes"], image["media_type"], record)
    return {"id": image_id, "imageUrl": f"/api/images/{image_id}"}


# ---- images (Jeevan) ----
@app.get("/api/images/{image_id}")
def image(image_id: str) -> Response:
    try:
        data, media_type, _ = store.load(get_settings().storage_dir, image_id)
    except KeyError:
        raise HTTPException(404, "No such image") from None
    return Response(content=data, media_type=media_type)


app.mount("/", StaticFiles(directory=Path(__file__).with_name("static"), html=True), name="static")
