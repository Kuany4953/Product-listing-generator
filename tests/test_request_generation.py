"""No-key tests for the request_generation tool, through the real protocol in memory (spec.md, "The gate").

The tool leads to spending money, so it never generates: it screens the brief and records a pending
request for a person to approve. These tests check the misuse cases and that nothing left the machine.
"""
import json
import socket
import uuid

import pytest
from mcp import Client

import server
from app import generator
from server import mcp
from tests.conftest import GOOD_BRIEF

pytestmark = pytest.mark.anyio

LIMITS = {"product_name": 80, "color": 40, "material": 40, "background": 80,
          "style": 80, "extra_details": 300}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def pending(env, tmp_path, monkeypatch):
    path = tmp_path / "pending.jsonl"
    monkeypatch.setattr(server, "PENDING", path)
    return path


async def call(args):
    async with Client(mcp) as client:
        return await client.call_tool("request_generation", args)


async def test_request_generation_is_listed_with_the_spec_schema():
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    tool = tools["request_generation"]
    props = tool.input_schema["properties"]
    for name, longest in LIMITS.items():
        assert longest in (props[name].get("maxLength"),
                           *(o.get("maxLength") for o in props[name].get("anyOf", []))), name
    v = props["variations"]
    assert (v["type"], v["minimum"], v["maximum"], v["default"]) == ("integer", 1, 5, 1)
    assert sorted(tool.input_schema["required"]) == ["background", "color", "material", "product_name"]
    assert "pending" in tool.description and "only when" in tool.description.lower()


async def test_wrong_type_is_an_error_and_nothing_is_recorded(pending):
    result = await call({**GOOD_BRIEF, "variations": "two"})
    assert result.is_error
    assert not pending.exists()


@pytest.mark.parametrize("change", [{"variations": 9}, {"variations": 0}, {"product_name": "x" * 200},
                                    {"extra_details": "y" * 301}, {"color": "   "}])
async def test_out_of_range_is_an_error_and_nothing_is_recorded(pending, change):
    result = await call({**GOOD_BRIEF, **change})
    assert result.is_error
    assert not pending.exists()


async def test_a_screened_out_brief_is_a_normal_result_and_nothing_is_recorded(pending):
    result = await call({**GOOD_BRIEF, "extra_details": "A woman holding it"})
    assert not result.is_error
    out = result.structured_content
    assert out["rejected"] is True and out["pending"] is False and out["generated"] is False
    assert "people or real brands" in out["reason"]
    assert not pending.exists()


async def test_pending_file_not_writable_is_an_error_result(env, tmp_path, monkeypatch):
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("a file where the pending folder should be")
    monkeypatch.setattr(server, "PENDING", blocked / "pending.jsonl")
    result = await call(GOOD_BRIEF)
    assert result.is_error
    text = result.content[0].text
    assert "could not be recorded" in text and "nothing was generated" in text
    assert str(tmp_path) not in text


async def test_records_a_pending_request_and_nothing_leaves_the_machine(env, pending, tmp_path, monkeypatch):
    env.setenv("OPENROUTER_API_KEY", "test-value-that-must-not-appear")
    connects, generated = [], []
    monkeypatch.setattr(socket.socket, "connect", lambda self, addr: connects.append(addr))
    monkeypatch.setattr(generator.OpenRouterGenerator, "generate",
                        lambda self, prompt, seed: generated.append(prompt))

    result = await call({**GOOD_BRIEF, "variations": 2})     # "leather handles" passes: whole words

    assert not result.is_error
    out = result.structured_content
    assert (out["generated"], out["pending"], out["variations"]) == (False, True, 2)
    assert out["estimated_cost_usd"] == pytest.approx(0.028)
    assert connects == [] and generated == []
    assert not (tmp_path / "generated").exists()                   # no image saved
    lines = pending.read_text().splitlines()
    assert len(lines) == 1
    request = json.loads(lines[0])
    assert request["status"] == "pending" and request["id"] == out["request_id"]
    assert uuid.UUID(request["id"]).version == 4
    assert request["brief"]["product_name"] == GOOD_BRIEF["product_name"] and request["variations"] == 2
    assert "test-value-that-must-not-appear" not in result.content[0].text + lines[0]
