"""No API key in any tracked file (intent/generate.md acceptance criterion). Runs in the gate and in CI."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}")


def test_no_key_in_tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = out.splitlines()
    hits = []
    for name in files:
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        hits += [f"{name}: {m.group(0)[:12]}..." for m in KEY.finditer(text)]
    assert hits == []


def test_the_pattern_would_catch_a_key():
    assert KEY.search("key = 'sk-or-v1-" + "a1" * 20 + "'")
