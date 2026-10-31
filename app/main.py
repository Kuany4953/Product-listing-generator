"""FastAPI app and routes (spec.md, "API endpoints").

The generator and critic are FastAPI dependencies, so tests replace them with fakes and
never call a model. Routes that call a model are plain `def`, so FastAPI runs them in its
thread pool and five generations at once do not block each other.
"""
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.brief import GenerateRequest
from app.config import get_settings
from app.screener import screen

app = FastAPI(title="Product Listing Image Generator")


@app.exception_handler(RequestValidationError)
def bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
    """A brief that breaks the rules is a 400 (spec), not FastAPI's default 422 (kept for screening)."""
    fields = sorted({".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()})
    return JSONResponse(status_code=400, content={"detail": f"Check these fields: {', '.join(fields)}"})


def get_generator():
    """The image generator. Wired to OpenRouter in week06-jeevan."""
    return None


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
    raise HTTPException(501, "Image generation is added in the week06-jeevan pull request.")


app.mount("/", StaticFiles(directory=Path(__file__).with_name("static"), html=True), name="static")
