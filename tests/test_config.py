import pytest

from app.config import get_settings


def test_api_config_returns_the_variation_count(client, env):
    assert client.get("/api/config").json() == {"variations": 5}
    env.setenv("VARIATIONS", "1")
    assert client.get("/api/config").json() == {"variations": 1}


def test_defaults_match_spec(env):
    names = ("VARIATIONS", "IMAGE_MODEL", "CRITIQUE_MODEL", "SECOND_CRITIQUE_MODEL", "IMAGE_ASPECT_RATIO")
    for name in names:
        env.delenv(name, raising=False)
    s = get_settings()
    assert s.variations == 5
    assert s.image_model == "black-forest-labs/flux.2-klein-4b"
    assert s.critique_model == "minimax/minimax-m3"
    assert s.second_critique_model == "xiaomi/mimo-v2.6-flash"
    assert s.image_aspect_ratio == "1:1"


def test_empty_second_critic_turns_it_off(env):
    env.setenv("SECOND_CRITIQUE_MODEL", "")
    assert get_settings().second_critique_model is None


@pytest.mark.parametrize("bad", ["0", "6", "five"])
def test_variations_outside_1_to_5_is_an_error(env, bad):
    env.setenv("VARIATIONS", bad)
    with pytest.raises(ValueError):
        get_settings()


def test_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Generate" in r.text
