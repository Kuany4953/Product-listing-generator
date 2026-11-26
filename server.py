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
from pathlib import Path
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from app import store
from app.config import get_settings

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    mcp.run()                     # stdio: the host starts this file and talks over its stdin and stdout
