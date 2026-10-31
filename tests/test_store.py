import struct
import uuid

import pytest

from app import store
from tests.conftest import PNG_1PX

INFO = {"ai_generated": "true", "model": "black-forest-labs/flux.2-klein-4b", "seed": "4150",
        "created": "2026-10-31T12:00:00Z", "tool": "Product Listing Image Generator"}

# A minimal JPEG: SOI, APP0 (JFIF), then a fake scan and EOI. The store never decodes pixels.
JPEG = (b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + b"pixels" + b"\xff\xd9")


def test_new_ids_are_uuid4():
    i = store.new_id()
    assert uuid.UUID(i).version == 4 and store.is_valid_id(i)


@pytest.mark.parametrize("bad", ["../../etc/passwd", "abc", "", "..", str(uuid.uuid4()).upper(),
                                 str(uuid.uuid4()) + "/../x", str(uuid.uuid1())])
def test_anything_but_a_lowercase_uuid4_is_rejected(bad):
    assert not store.is_valid_id(bad)


def test_save_and_load_round_trip(tmp_path):
    i = store.save(tmp_path, PNG_1PX, "image/png", {"variation": 1, "model": "m", "seed": 7})
    data, media_type, record = store.load(tmp_path, i)
    assert media_type == "image/png" and record["variation"] == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([f"{i}.png", f"{i}.json"])


def test_load_refuses_a_bad_or_unknown_id(tmp_path):
    with pytest.raises(KeyError):
        store.load(tmp_path, "../secret")
    with pytest.raises(KeyError):
        store.load(tmp_path, store.new_id())


def test_png_provenance_is_embedded_and_pixels_unchanged():
    out = store.embed_provenance(PNG_1PX, "image/png", INFO)
    assert out[:8] == PNG_1PX[:8] and out[8:33] == PNG_1PX[8:33]        # signature, IHDR first
    assert out.endswith(PNG_1PX[-12:])                                  # IEND last
    assert PNG_1PX[33:-12] in out                                       # IDAT bytes untouched
    assert store.read_provenance(out, "image/png") == INFO


def test_jpeg_provenance_goes_after_app_segments_and_is_readable():
    out = store.embed_provenance(JPEG, "image/jpeg", INFO)
    assert out[:2] == b"\xff\xd8" and out[2:4] == b"\xff\xe0"           # APP0 still first
    assert out.endswith(JPEG[20:])                                      # scan and EOI untouched
    assert store.read_provenance(out, "image/jpeg") == INFO


def test_unknown_format_is_saved_unchanged():
    assert store.embed_provenance(b"RIFFxxxxWEBP", "image/webp", INFO) == b"RIFFxxxxWEBP"


def test_c2pa_check_looks_for_a_manifest_box():
    assert not store.has_c2pa_manifest(PNG_1PX)
    assert store.has_c2pa_manifest(b"....jumb....c2pa....")


@pytest.mark.parametrize("path", ["/api/images/not-a-uuid", "/api/images/..%2F..%2Fapp%2Fmain.py",
                                  f"/api/images/{uuid.uuid4()}"])
def test_image_route_returns_404_for_bad_or_unknown_ids(client, path):
    assert client.get(path).status_code == 404
