import pytest

from app.brief import ProductBrief
from app.screener import REJECTION, screen
from tests.conftest import GOOD_BRIEF


def brief(**changes):
    return ProductBrief(**{**GOOD_BRIEF, **changes})


def test_the_intents_own_example_passes():
    # The revision-1 screener matched substrings and would have rejected this (PR #2 review).
    assert screen(brief()) is None


@pytest.mark.parametrize("text", ["Handwoven basket", "leather handles", "Canvas handbag", "Mango wood bowl",
                                  "Manual coffee grinder", "Childproof lid", "Facial roller"])
def test_words_containing_a_people_word_pass(text):
    assert screen(brief(product_name=text)) is None, text


def test_known_limit_a_product_named_model_is_rejected():
    # "Model 3 charger" uses "model" as a word, so it is rejected. Accepted limit (README, "Known limits").
    assert screen(brief(product_name="Model 3 charger")) == REJECTION


@pytest.mark.parametrize("field,text", [
    ("extra_details", "A man holding it"), ("background", "Kitchen with a woman cooking"),
    ("style", "Worn by a model"), ("extra_details", "Shown in someone's hands"),
    ("background", "A child's bedroom with the child"), ("extra_details", "Close-up of a face"),
    ("style", "PERSON in frame")])
def test_people_are_rejected(field, text):
    assert screen(brief(**{field: text})) == REJECTION


@pytest.mark.parametrize("text", ["Nike running shoe", "Gucci-style tote", "Taylor Swift tote bag",
                                  "Basket like the IKEA one"])
def test_blocklisted_names_are_rejected(text):
    assert screen(brief(extra_details=text)) == REJECTION


def test_multi_word_names_match_only_as_a_phrase():
    assert screen(brief(extra_details="Swift delivery, Taylor-made fit")) is None


def test_endpoint_returns_422_and_never_calls_the_generator(client, generator):
    r = client.post("/api/generate", json={"brief": {**GOOD_BRIEF, "extra_details": "A man holding it"},
                                           "variation": 1})
    assert r.status_code == 422
    assert r.json()["detail"] == REJECTION
    assert generator.calls == []
