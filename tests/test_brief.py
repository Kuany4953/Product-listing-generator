import pytest
from pydantic import ValidationError

from app.brief import ProductBrief
from tests.conftest import GOOD_BRIEF


def test_good_brief_is_valid_and_trimmed():
    b = ProductBrief(**{**GOOD_BRIEF, "color": "  Navy blue  "})
    assert b.color == "Navy blue"


@pytest.mark.parametrize("field", ["product_name", "color", "material", "background"])
def test_missing_required_field_fails(field):
    data = {k: v for k, v in GOOD_BRIEF.items() if k != field}
    with pytest.raises(ValidationError):
        ProductBrief(**data)


@pytest.mark.parametrize("field", ["product_name", "color", "material", "background"])
def test_blank_required_field_fails(field):
    with pytest.raises(ValidationError):
        ProductBrief(**{**GOOD_BRIEF, field: "   "})


def test_optional_fields_may_be_left_out():
    b = ProductBrief(product_name="Basket", color="Red", material="Wicker", background="Plain white")
    assert b.style is None and b.extra_details is None


@pytest.mark.parametrize("field,limit", [("product_name", 80), ("color", 40), ("material", 40),
                                         ("background", 80), ("style", 80), ("extra_details", 300)])
def test_length_limits(field, limit):
    ProductBrief(**{**GOOD_BRIEF, field: "a" * limit})
    with pytest.raises(ValidationError):
        ProductBrief(**{**GOOD_BRIEF, field: "a" * (limit + 1)})


def test_endpoint_returns_400_for_a_bad_brief_and_never_calls_the_generator(client, generator):
    brief = {k: v for k, v in GOOD_BRIEF.items() if k != "color"}
    r = client.post("/api/generate", json={"brief": brief, "variation": 1})
    assert r.status_code == 400
    assert generator.calls == []


@pytest.mark.parametrize("variation", [0, 6])
def test_endpoint_returns_400_for_a_variation_out_of_range(client, generator, variation):
    r = client.post("/api/generate", json={"brief": GOOD_BRIEF, "variation": variation})
    assert r.status_code == 400
    assert generator.calls == []
