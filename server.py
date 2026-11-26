"""The listing generator behind an MCP server, so any MCP host can call it (spec.md, "Team Project 2").

    python3 client.py                  # a host with no model: list the tools, call each once
    python3 -m pytest tests/test_find_images.py tests/test_request_generation.py

The tools reuse TP1's code: the brief rules (app.brief), the whole-word screener (app.screener) and
the UUID-only store (app.store). The SDK builds each tool's JSON Schema from the type hints and
rejects a bad argument before the function runs. The docstring is what the model reads to decide
when to call a tool.

Stdout belongs to the protocol: nothing here prints. Logging goes to stderr.
"""
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError

from app import store
from app.brief import ProductBrief
from app.config import get_settings
from app.screener import screen

PENDING = Path(__file__).with_name("pending.jsonl")   # git-ignored; a person reviews it (spec.md, "The gate")
COST_PER_IMAGE = 0.014                                  # FLUX.2 klein, spec.md "Cost"

log = logging.getLogger("listing")

mcp = MCPServer("listing")


def _records(storage: Path) -> list[dict]:
    """Every saved image record in the store. No store yet is an empty list; an unreadable one raises."""
    if not storage.exists():
        return []
    out = []
    for meta in storage.iterdir():
        if meta.suffix != ".json" or not store.is_valid_id(meta.stem):
            continue
        try:
            out.append(json.loads(meta.read_text()))
        except (ValueError, UnicodeDecodeError):
            log.warning("skipping unreadable record %s", meta.name)
    return out


@mcp.tool()
def find_images(
    product: Annotated[str, Field(min_length=1, max_length=80,
                                  description="The product name, or part of it, e.g. 'storage basket'")],
    limit: Annotated[int, Field(ge=1, le=20, description="The most images to return")] = 5,
) -> dict[str, Any]:
    """Find listing images already generated for a product, newest first, by product name.
    Call this first whenever a seller wants images of a product, before request_generation:
    if suitable images exist, offer those instead of paying for new ones. found is false when
    nothing matches; that is an answer to give the seller, not an error."""
    want = product.strip().casefold()
    if not want:
        raise ToolError("product is blank: give the product's name, or part of it")
    try:
        records = _records(get_settings().storage_dir)
    except OSError as exc:
        log.warning("image store unreadable: %s", type(exc).__name__)
        raise ToolError("The image store could not be read, so no saved images can be listed. "
                        "Do not retry; tell the seller and ask a person on the team to check it.") from None
    hits = [r for r in records if want in str(r.get("brief", {}).get("product_name", "")).casefold()]
    hits.sort(key=lambda r: str(r.get("created", "")), reverse=True)
    images = [{"id": r.get("id"), **{k: r.get("brief", {}).get(k) for k in
                                     ("product_name", "color", "material", "background")},
               "variation": r.get("variation"), "model": r.get("model"), "created": r.get("created")}
              for r in hits[:limit]]
    log.info("find_images %r: %d of %d", product, len(images), len(hits))
    return {"found": bool(images), "count": len(images), "images": images}


def _text(longest: int, what: str):
    return Annotated[str, Field(min_length=1, max_length=longest, description=what)]


def _optional(longest: int, what: str):
    return Annotated[str | None, Field(max_length=longest, description=what)]


@mcp.tool()
def request_generation(
    product_name: _text(80, "What the product is, e.g. 'Handwoven storage basket'"),
    color: _text(40, "The product's main color"),
    material: _text(40, "What the product is made of"),
    background: _text(80, "The scene behind the product, e.g. 'Plain white'"),
    style: _optional(80, "Optional look, e.g. 'Minimal, natural light'") = None,
    extra_details: _optional(300, "Optional details to show, e.g. 'Has two leather handles'") = None,
    variations: Annotated[int, Field(ge=1, le=5, description="How many images (each one is billed)")] = 1,
) -> dict[str, Any]:
    """Ask for new listing images of a product. Call this only when the seller has asked for new
    images and find_images found nothing suitable. Images cost money, so nothing is generated here:
    the request is recorded as pending for a person on the team to approve. Tell the seller it is
    pending, not done. A brief that mentions people or real brands is refused; tell the seller why."""
    try:
        brief = ProductBrief(product_name=product_name, color=color, material=material, background=background,
                             style=style, extra_details=extra_details)
    except ValidationError as exc:                       # e.g. a required field that is only spaces
        fields = ", ".join(sorted({str(e["loc"][0]) for e in exc.errors()}))
        raise ToolError(f"Check these fields: {fields}. Required fields cannot be blank.") from None
    rejection = screen(brief)
    if rejection:
        log.info("request_generation screened out")
        return {"generated": False, "pending": False, "rejected": True, "reason": rejection}
    request = {"id": store.new_id(), "status": "pending",
               "requested": datetime.now(UTC).isoformat(timespec="seconds"),
               "brief": brief.model_dump(), "variations": variations,
               "estimated_cost_usd": round(variations * COST_PER_IMAGE, 3)}
    try:
        with open(PENDING, "a", encoding="utf-8") as f:
            f.write(json.dumps(request) + "\n")
    except OSError as exc:
        log.warning("pending file not writable: %s", type(exc).__name__)
        raise ToolError("The request could not be recorded, and nothing was generated. "
                        "Do not retry; tell the seller and ask a person on the team to check it.") from None
    log.info("request_generation recorded %s (%d images)", request["id"], variations)
    return {"generated": False, "pending": True, "request_id": request["id"], "variations": variations,
            "estimated_cost_usd": request["estimated_cost_usd"],
            "note": "Recorded for a person on the team to approve. "
                    "No image was generated and nothing was spent."}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    mcp.run()                     # stdio: the host starts this file and talks over its stdin and stdout
