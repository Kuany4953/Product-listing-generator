from app.brief import ProductBrief
from app.prompts import COMPOSITIONS, SUFFIX, build_prompt, prompts_for
from tests.conftest import GOOD_BRIEF

BRIEF = ProductBrief(**GOOD_BRIEF)


def test_five_compositions_in_spec_order():
    assert [c.split(",")[0] for c in COMPOSITIONS] == [
        "Front view", "Top-down view", "Close-up showing the material texture",
        "Three-quarter angled view", "Lifestyle scene in the chosen background"]


def test_prompt_carries_every_brief_field_and_ends_with_the_product_only_rule():
    p = build_prompt(BRIEF, 1)
    for value in GOOD_BRIEF.values():
        assert value in p, value
    assert p.endswith(SUFFIX)
    assert SUFFIX == "Show only the product. No people, no hands, no text, no logos."


def test_optional_fields_are_left_out_when_empty():
    mug = ProductBrief(product_name="Mug", color="Red", material="Ceramic", background="Plain white")
    p = build_prompt(mug, 1)
    assert "Style" not in p and "Details" not in p


def test_each_variation_uses_its_own_composition():
    assert all(COMPOSITIONS[v - 1] in build_prompt(BRIEF, v) for v in range(1, 6))


def test_lifestyle_scene_still_says_no_people():
    assert "no people" in COMPOSITIONS[4]


def test_variation_count_1_builds_exactly_one_prompt():
    assert len(prompts_for(BRIEF, 1)) == 1
    assert len(prompts_for(BRIEF, 5)) == 5
