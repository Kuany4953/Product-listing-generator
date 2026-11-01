"""Saves each image with its brief and keeps its provenance (spec.md, "Saving images").

Ids are UUID4 strings made here. Any id from a client is checked with is_valid_id before it
touches the file system, so "../" can never reach another file.

FLUX.2 klein returns JPEGs with a signed C2PA manifest whose hash covers the file's bytes, so
an image that has one is saved exactly as returned. Only an image without C2PA gets our own
unsigned label, written without changing pixels: PNG tEXt chunks right after IHDR, or a JPEG
comment segment right after the APPn segments. The JSON sidecar records provenance either way.
"""
import json
import struct
import uuid
import zlib
from datetime import UTC, datetime
from pathlib import Path

TOOL = "Product Listing Image Generator (CPSC 415 TP1)"
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
JPEG_PREFIX = b"provenance:"


def new_id() -> str:
    return str(uuid.uuid4())


def is_valid_id(value: str) -> bool:
    """True only for a lowercase, canonical UUID4: the only ids this server ever makes."""
    try:
        u = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return u.version == 4 and str(u) == value


def save(storage_dir: Path, image: bytes, media_type: str, record: dict) -> str:
    """Write <id>.<ext> and <id>.json. Returns the new id. A C2PA image is written unchanged."""
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    image_id = new_id()
    created = record.get("created") or datetime.now(UTC).isoformat(timespec="seconds")
    info = {"ai_generated": "true", "model": str(record.get("model", "")),
            "seed": str(record.get("seed", "")), "created": created, "tool": TOOL}
    name = f"{image_id}.{EXT.get(media_type, 'bin')}"
    if has_c2pa_manifest(image):
        source, data = "c2pa", image                   # any added byte would break the signed hash
    else:
        source, data = "label", embed_provenance(image, media_type, info)
    (storage_dir / name).write_bytes(data)
    full = {**record, "id": image_id, "file": name, "media_type": media_type, "created": created,
            "provenance": {**info, "source": source}}
    (storage_dir / f"{image_id}.json").write_text(json.dumps(full, indent=2))
    return image_id


def load(storage_dir: Path, image_id: str) -> tuple[bytes, str, dict]:
    """The saved image, its media type and its record. KeyError for a bad or unknown id."""
    if not is_valid_id(image_id):
        raise KeyError(image_id)
    meta = Path(storage_dir) / f"{image_id}.json"
    if not meta.is_file():
        raise KeyError(image_id)
    record = json.loads(meta.read_text())
    return (Path(storage_dir) / record["file"]).read_bytes(), record["media_type"], record


# ---------- provenance ----------

def embed_provenance(image: bytes, media_type: str, info: dict) -> bytes:
    if media_type == "image/png" and image[:8] == b"\x89PNG\r\n\x1a\n":
        ihdr_end = 8 + 12 + struct.unpack(">I", image[8:12])[0]          # IHDR must stay first
        chunks = b"".join(_png_text(k, v) for k, v in info.items())
        return image[:ihdr_end] + chunks + image[ihdr_end:]
    if media_type == "image/jpeg" and image[:2] == b"\xff\xd8":
        at = _after_app_segments(image)
        payload = JPEG_PREFIX + json.dumps(info).encode()
        return image[:at] + b"\xff\xfe" + struct.pack(">H", len(payload) + 2) + payload + image[at:]
    return image


def read_provenance(image: bytes, media_type: str) -> dict:
    """What embed_provenance wrote, read back from the bytes (for tests and the README check)."""
    out = {}
    if media_type == "image/png":
        pos = 8
        while pos + 8 <= len(image):
            length, kind = struct.unpack(">I4s", image[pos:pos + 8])
            if kind == b"tEXt":
                key, _, value = image[pos + 8:pos + 8 + length].partition(b"\x00")
                out[key.decode("latin-1")] = value.decode("latin-1")
            pos += 12 + length
    elif media_type == "image/jpeg":
        pos = 2
        while pos + 4 <= len(image) and image[pos] == 0xFF:
            marker, length = image[pos + 1], struct.unpack(">H", image[pos + 2:pos + 4])[0]
            body = image[pos + 4:pos + 2 + length]
            if marker == 0xFE and body.startswith(JPEG_PREFIX):
                out.update(json.loads(body[len(JPEG_PREFIX):]))
            if marker == 0xDA:                                          # start of scan: no more headers
                break
            pos += 2 + length
    return out


def has_c2pa_manifest(image: bytes) -> bool:
    """A C2PA manifest is a JUMBF box labelled c2pa. Its presence is a sign, not a verification."""
    return b"jumb" in image and b"c2pa" in image


def _png_text(key: str, value: str) -> bytes:
    data = key.encode("latin-1") + b"\x00" + value.encode("latin-1", errors="replace")
    return struct.pack(">I", len(data)) + b"tEXt" + data + struct.pack(">I", zlib.crc32(b"tEXt" + data))


def _after_app_segments(image: bytes) -> int:
    """Offset just past SOI and any APP0-APP15 segments (JFIF/EXIF must stay first)."""
    pos = 2
    while pos + 4 <= len(image) and image[pos] == 0xFF and 0xE0 <= image[pos + 1] <= 0xEF:
        pos += 2 + struct.unpack(">H", image[pos + 2:pos + 4])[0]
    return pos
