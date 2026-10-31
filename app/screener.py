"""Rejects briefs that ask for people or real brands, before any billed call (spec.md, "Screening briefs").

Whole words only: "Handwoven ... leather handles" passes, "a man holding it" does not. The first
version of this rule, drafted by the agent, matched substrings and would have rejected the
intent's own example brief; the PR #2 review caught it.
"""
import re
from pathlib import Path

from app.brief import ProductBrief

REJECTION = ("This tool creates product-only images. "
             "Please remove references to people or real brands.")

PEOPLE = ["person", "people", "man", "men", "woman", "women", "child", "children", "kid", "kids", "boy",
          "girl", "baby", "human", "model", "models", "hand", "hands", "face", "faces", "wearing", "worn",
          "selfie", "portrait", "celebrity"]


def _blocklist() -> list[str]:
    lines = (Path(__file__).with_name("blocklist.txt")).read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def _whole(term: str) -> re.Pattern:
    # Word boundaries on both sides; a hyphen or apostrophe ends a word ("child's", "Gucci-style").
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)


PATTERNS = [_whole(t) for t in PEOPLE + _blocklist()]


def screen(brief: ProductBrief) -> str | None:
    """The rejection message if any field mentions a person or a blocklisted name, else None."""
    for text in brief.fields():
        if any(p.search(text) for p in PATTERNS):
            return REJECTION
    return None
