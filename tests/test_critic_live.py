"""The one billed test: a real critic must mark a deliberately wrong color as unmet.

    python -m pytest -m live      # needs OPENROUTER_API_KEY; one or two vision calls, under a cent

The image is the lab's front-view navy basket (images/, a real FLUX image for this project).
The brief says red. A critic that reads the image must answer the color item with met: false.
"""
import os
from pathlib import Path

import pytest

from app.brief import ProductBrief
from app.config import get_settings
from app.critic import OpenRouterCritic, critique_image
from app.critique_parser import build_checklist

ROOT = Path(__file__).resolve().parents[1]
IMAGES = sorted((ROOT / "images").glob("basket-01-front.*"))

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY is not set"),
    pytest.mark.skipif(not IMAGES, reason="the lab image set is not in images/"),
]


def test_wrong_color_brief_is_marked_unmet():
    image = IMAGES[0]
    media_type = "image/png" if image.suffix == ".png" else "image/jpeg"
    brief = ProductBrief(product_name="storage basket with two leather handles", color="Red",
                         material="Seagrass", background="Plain white")
    requirements = build_checklist(brief)
    critic = OpenRouterCritic(api_key=os.environ["OPENROUTER_API_KEY"])
    model = get_settings().critique_model
    result = critique_image(critic, model, image.read_bytes(), media_type, requirements)
    assert result is not None, "critique unavailable twice"
    assert "The product is Red" in result["unmet"]
