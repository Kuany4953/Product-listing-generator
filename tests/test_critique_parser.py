"""The plain code that checks a critique. No model, no key."""
import json

from app.brief import ProductBrief
from app.critique_parser import build_checklist, check, disagreements, extract_json
from tests.conftest import GOOD_BRIEF

BRIEF = ProductBrief(**GOOD_BRIEF)
REQS = build_checklist(BRIEF)


def reply(met=None, problems=(), extra=(), drop=(), score=None):
    """A critic reply: every requirement met unless listed in `met` as False."""
    met = met or {}
    checks = [{"requirement": r, "met": met.get(i, True), "evidence": "seen"}
              for i, r in enumerate(REQS) if i not in drop]
    checks += [{"requirement": e, "met": True, "evidence": "seen"} for e in extra]
    body = {"checks": checks, "problems": list(problems)}
    if score is not None:
        body["score"] = score
    return body


def test_checklist_is_built_from_the_brief_in_spec_order():
    assert REQS == [
        "The product is a Handwoven storage basket",
        "The product is Navy blue",
        "The product looks like it is made of Seagrass",
        "The background is Plain white",
        "The style is Minimal, natural light",
        "The image shows: Has two leather handles",
        "No people or hands appear in the image",
        "There is no text or logo in the image",
    ]


def test_style_item_only_when_style_is_given():
    no_style = ProductBrief(**{**GOOD_BRIEF, "style": None})
    assert not any(r.startswith("The style") for r in build_checklist(no_style))


def test_extra_details_item_only_when_given():
    # The critic sees only the checklist: without this item it called the requested handles a "problem".
    no_details = ProductBrief(**{**GOOD_BRIEF, "extra_details": None})
    assert not any(r.startswith("The image shows") for r in build_checklist(no_details))


def test_all_met_scores_10():
    r = check(REQS, reply())
    assert r["usable"] and r["score"] == 10
    assert r["unmet"] == r["missing"] == r["invented"] == []


def test_one_unmet_is_named_and_lowers_the_score():
    r = check(REQS, reply(met={1: False}))
    assert r["unmet"] == ["The product is Navy blue"]
    assert r["score"] == 9                       # 6 of 7 met: 8.57, rounded half up


def test_the_models_own_score_is_ignored():
    assert check(REQS, reply(met={0: False, 1: False, 2: False}, score=10))["score"] == 6


def test_met_must_be_literally_true():
    body = reply()
    body["checks"][1]["met"] = "yes"
    assert check(REQS, body)["unmet"] == ["The product is Navy blue"]


def test_a_missing_requirement_is_reported_and_counts_as_not_met():
    r = check(REQS, reply(drop={3}))
    assert r["missing"] == ["The background is Plain white"]
    assert r["score"] == 9


def test_an_invented_requirement_is_reported():
    r = check(REQS, reply(extra=["The lighting is dramatic"]))
    assert r["invented"] == ["The lighting is dramatic"]
    assert r["score"] == 10                      # reported to the seller, not scored


def test_requirement_text_is_matched_loosely():
    body = reply()
    body["checks"][1]["requirement"] = "the product is NAVY BLUE."
    assert check(REQS, body)["unmet"] == []


def test_problems_lower_the_score_by_one_each_at_most_three():
    assert check(REQS, reply(problems=["extra basket"]))["score"] == 9
    assert check(REQS, reply(problems=["a", "b", "c", "d", "e"]))["score"] == 7
    assert check(REQS, reply(met=dict.fromkeys(range(7), False), problems=["a"]))["score"] == 0


def test_problems_that_are_not_strings_are_dropped():
    assert check(REQS, reply(problems=["extra basket", 3, None]))["problems"] == ["extra basket"]


def test_non_json_or_no_checks_list_is_unusable_not_a_crash():
    assert not check(REQS, extract_json("I can't see an image."))["usable"]
    assert not check(REQS, extract_json('{"verdict": "great"}'))["usable"]
    assert not check(REQS, extract_json('{"checks": [ {"requirement": '))["usable"]


def test_json_in_prose_and_fences_is_extracted():
    text = "Here is my review:\n```json\n" + json.dumps(reply()) + "\n```\nThanks!"
    assert check(REQS, extract_json(text))["usable"]


def test_disagreements_list_requirements_where_two_critics_differ():
    a = check(REQS, reply(met={1: False}))
    b = check(REQS, reply(met={3: False}))
    assert disagreements(a, b) == ["The product is Navy blue", "The background is Plain white"]
    assert disagreements(a, a) == []
