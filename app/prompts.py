"""Builds the image prompt for each variation (spec.md, "Variations").

One base prompt from the brief, plus one composition per variation, in spec order. Every
prompt ends with the product-only rule, so the image model is told what the screener enforces.
"""
from app.brief import ProductBrief

COMPOSITIONS = [
    "Front view, centered, at eye level",
    "Top-down view, looking straight down at the product",
    "Close-up showing the material texture, filling most of the frame",
    "Three-quarter angled view, showing the front and one side",
    "Lifestyle scene in the chosen background, the product in use in its setting, no people",
]

SUFFIX = "Show only the product. No people, no hands, no text, no logos."


def build_prompt(brief: ProductBrief, variation: int) -> str:
    """The prompt for one variation (1-5)."""
    parts = [
        f"Product photograph for an online listing: a {brief.color} {brief.product_name}, "
        f"made of {brief.material}.",
        f"{COMPOSITIONS[variation - 1]}.",
        f"Background: {brief.background}.",
    ]
    if brief.style:
        parts.append(f"Style: {brief.style}.")
    if brief.extra_details:
        parts.append(f"Details: {brief.extra_details}.")
    parts.append(SUFFIX)
    return " ".join(parts)


def prompts_for(brief: ProductBrief, variations: int) -> list[str]:
    """The first N prompts, for a variation setting of N."""
    return [build_prompt(brief, v) for v in range(1, variations + 1)]
