"""Checks a critique in plain code (spec.md, "Checking the response"). No model, no key.

The critic is a model and can be wrong, vague, or off-format. This module never takes a
number or a verdict from it as given: it extracts the JSON, compares the checklist the
critic answered with the checklist we asked, and computes the score itself.
"""
import json
import math
import re

from app.brief import ProductBrief

MAX_PROBLEM_PENALTY = 3


def build_checklist(brief: ProductBrief) -> list[str]:
    """Yes/no requirements a person could answer by looking, in spec order."""
    items = [
        f"The product is a {brief.product_name}",
        f"The product is {brief.color}",
        f"The product looks like it is made of {brief.material}",
        f"The background is {brief.background}",
    ]
    if brief.style:
        items.append(f"The style is {brief.style}")
    if brief.extra_details:
        items.append(f"The image shows: {brief.extra_details}")
    items +=["No people or hands appear in the image", "There is no text or logo in the image"]
    return items


def extract_json(text: str | None) -> dict | None:
    """The JSON object from the first '{' to the last '}', or None. Handles fences and prose."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def check(requirements: list[str], critique: dict | None) -> dict:
    """What the code can say for sure about a critique. `usable` is False for anything off-format."""
    if critique is None or not isinstance(critique.get("checks"), list):
        return {"usable": False}
    answered = {}
    for c in critique["checks"]:
        if isinstance(c, dict) and isinstance(c.get("requirement"), str):
            answered.setdefault(_norm(c["requirement"]), c)
    checks, missing, unmet = [], [], []
    for r in requirements:
        c = answered.get(_norm(r))
        if c is None:
            missing.append(r)
            continue
        met = c.get("met") is True                       # only a literal true counts
        evidence = c.get("evidence") if isinstance(c.get("evidence"), str) else ""
        checks.append({"requirement": r, "met": met, "evidence": evidence})
        if not met:
            unmet.append(r)
    wanted = {_norm(r) for r in requirements}
    invented = [c["requirement"] for k, c in answered.items() if k not in wanted]
    problems = [p for p in critique.get("problems") or [] if isinstance(p, str)] \
        if isinstance(critique.get("problems"), list) else []
    met_count = len(requirements) - len(missing) - len(unmet)
    score = math.floor(10 * met_count / len(requirements) + 0.5) - min(len(problems), MAX_PROBLEM_PENALTY)
    return {"usable": True, "checks": checks, "missing": missing, "unmet": unmet, "invented": invented,
            "problems": problems, "score": max(score, 0)}


def disagreements(a: dict, b: dict) -> list[str]:
    """Requirements the two critics answered differently, in checklist order."""
    met_b = {c["requirement"]: c["met"] for c in b.get("checks", [])}
    return [c["requirement"] for c in a.get("checks", [])
            if c["requirement"] in met_b and met_b[c["requirement"]] != c["met"]]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
