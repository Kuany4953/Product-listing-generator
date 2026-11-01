import os

import pytest

from app import config
from app.config import get_settings


def test_the_test_session_never_loads_the_key_from_dotenv():
    # The gate runs `env -u OPENROUTER_API_KEY pytest` so no test can bill. If config.py
    # loaded .env on import, the key would come back and a `live` test would run and bill.
    assert os.environ.get("APP_NO_DOTENV") == "1"


def test_load_env_reads_dotenv_unless_disabled(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("FAKE_SETTING_FOR_TEST=from-dotenv\n")
    monkeypatch.delenv("FAKE_SETTING_FOR_TEST", raising=False)
    config.load_env(dotenv)                          # APP_NO_DOTENV=1 in tests: nothing loaded
    assert "FAKE_SETTING_FOR_TEST" not in os.environ
    monkeypatch.delenv("APP_NO_DOTENV")
    config.load_env(dotenv)
    assert os.environ["FAKE_SETTING_FOR_TEST"] == "from-dotenv"
    monkeypatch.delenv("FAKE_SETTING_FOR_TEST")


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
