"""No-key tests for the find_images tool, through the real protocol in memory (spec.md, "Team Project 2").

`Client(mcp)` connects to the server object directly: every call is listed, validated and invoked
exactly as a host would do it, with no subprocess, no network and no model. Each session runs on its own
event loop (tests/conftest.py, run_async), because the browser tests leave one running.
"""
import pytest
from mcp import Client

import server
from app import store
from server import mcp
from tests.conftest import GOOD_BRIEF, PNG_1PX, run_async


@pytest.fixture
def storage(env, tmp_path):
    """STORAGE_DIR is a temp folder (the env fixture sets it); nothing in generated/ is touched."""
    return tmp_path / "generated"


@pytest.fixture
def reads(monkeypatch):
    """Counts how often the tool asks for its settings, i.e. whether the function body ran."""
    calls = []
    real = server.get_settings

    def spy():
        calls.append(1)
        return real()

    monkeypatch.setattr(server, "get_settings", spy)
    return calls


def save(storage, created, **brief):
    record = {"brief": {**GOOD_BRIEF, **brief}, "variation": 1, "prompt": "p", "seed": 7,
              "model": "fake/image", "created": created}
    return store.save(storage, PNG_1PX, "image/png", record)


def call(name, args):
    async def session():
        async with Client(mcp) as client:
            return await client.call_tool(name, args)
    return run_async(session())


def listed():
    async def session():
        async with Client(mcp) as client:
            return {t.name: t for t in (await client.list_tools()).tools}
    return run_async(session())


def test_find_images_is_listed_with_the_spec_schema():
    tools = listed()
    tool = tools["find_images"]
    props = tool.input_schema["properties"]
    assert props["product"]["type"] == "string"
    assert (props["product"]["minLength"], props["product"]["maxLength"]) == (1, 80)
    assert props["limit"]["type"] == "integer"
    assert (props["limit"]["minimum"], props["limit"]["maximum"], props["limit"]["default"]) == (1, 20, 5)
    assert tool.input_schema["required"] == ["product"]
    assert "before" in tool.description and "request_generation" in tool.description   # says when


def test_finds_saved_images_newest_first_without_paths(storage):
    old = save(storage, "2026-11-01T10:00:00+00:00")
    new = save(storage, "2026-11-02T10:00:00+00:00", color="Red")
    save(storage, "2026-11-03T10:00:00+00:00", product_name="Ceramic mug")
    result = call("find_images", {"product": "BASKET"})
    assert not result.is_error
    out = result.structured_content
    assert out["found"] is True and out["count"] == 2
    assert [i["id"] for i in out["images"]] == [new, old]
    assert out["images"][0]["color"] == "Red"
    assert str(storage) not in result.content[0].text and "file" not in out["images"][0]


def test_limit_caps_the_number_returned(storage):
    for day in range(1, 4):
        save(storage, f"2026-11-0{day}T10:00:00+00:00")
    result = call("find_images", {"product": "basket", "limit": 2})
    assert result.structured_content["count"] == 2


def test_wrong_type_is_an_error_and_the_function_does_not_run(storage, reads):
    result = call("find_images", {"product": "basket", "limit": "five"})
    assert result.is_error
    assert reads == []


@pytest.mark.parametrize("args", [{"product": "basket", "limit": 50}, {"product": "basket", "limit": 0},
                                  {"product": ""}, {"product": "x" * 81}])
def test_out_of_range_is_an_error_and_the_function_does_not_run(storage, reads, args):
    result = call("find_images", args)
    assert result.is_error
    assert reads == []


def test_no_match_is_a_normal_result_not_an_error(storage):
    save(storage, "2026-11-01T10:00:00+00:00")
    result = call("find_images", {"product": "teapot"})
    assert not result.is_error
    assert result.structured_content == {"found": False, "count": 0, "images": []}


def test_no_store_yet_is_a_normal_result(storage):
    assert not storage.exists()
    result = call("find_images", {"product": "basket"})
    assert not result.is_error and result.structured_content["found"] is False


def test_unreadable_store_is_an_error_result_the_model_can_act_on(env, tmp_path):
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("a file where the image store should be")
    env.setenv("STORAGE_DIR", str(blocked))
    result = call("find_images", {"product": "basket"})
    assert result.is_error
    text = result.content[0].text
    assert "image store" in text and "person" in text
    assert str(blocked) not in text                                  # no server paths in a result
