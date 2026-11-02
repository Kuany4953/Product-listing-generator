"""No-key checks on the Week 6 lab image sets committed under images/.

Every manifest must record what the lab and spec.md require per image (prompt, seed, model, media type,
the cost from the reply), every file it names must exist, and FLUX images must keep their signed C2PA
manifest byte for byte (spec.md, storage; the same rule store.py enforces for the app's images).
"""
import json
from pathlib import Path

import pytest

from app import store

IMAGES = Path(__file__).resolve().parents[1] / "images"
MANIFESTS = sorted(IMAGES.glob("**/manifest.json"))
REQUIRED = ("name", "prompt", "seed", "requirements", "model", "file", "media_type", "cost")


def test_the_mug_set_is_committed():
    assert IMAGES / "mug" / "manifest.json" in MANIFESTS


@pytest.mark.parametrize("manifest", MANIFESTS, ids=[str(m.relative_to(IMAGES)) for m in MANIFESTS])
def test_manifest_records_each_image(manifest):
    entries = json.loads(manifest.read_text())
    assert len(entries) == 5, "a lab set is five prompts from one family"
    assert len({e["seed"] for e in entries}) == 5, "each prompt has its own fixed seed"
    for e in entries:
        missing = [k for k in REQUIRED if k not in e]
        assert not missing, f"{e.get('name')}: manifest lacks {missing}"
        assert isinstance(e["seed"], int)
        assert isinstance(e["cost"], (int, float)) and e["cost"] > 0, f"{e['name']}: cost from the reply"
        assert e["requirements"], f"{e['name']}: no requirements to critique against"
        image = manifest.parent / e["file"]
        assert image.exists(), f"{image} is named in the manifest but missing"
        if e["model"].startswith("black-forest-labs/"):
            assert store.has_c2pa_manifest(image.read_bytes()), f"{image.name} lost its C2PA manifest"
