"""OpenRouterCritic with a fake SDK client: the request carries the image itself. No key, no call."""
import base64
from types import SimpleNamespace

from app.critic import OpenRouterCritic
from tests.conftest import PNG_1PX


class FakeChat:
    def __init__(self):
        self.kwargs = []

    def send(self, **kwargs):
        self.kwargs.append(kwargs)
        message = SimpleNamespace(content='{"checks": []}')
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])


def critic():
    fake = SimpleNamespace(chat=FakeChat())
    return OpenRouterCritic(api_key="unused", client=fake), fake.chat


def test_the_vision_request_contains_the_image_as_base64_data():
    c, chat = critic()
    assert c.ask("minimax/minimax-m3", PNG_1PX, "image/png", "Check this") == '{"checks": []}'
    content = chat.kwargs[0]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "Check this"}
    url = content[1]["image_url"]["url"]
    assert content[1]["type"] == "image_url"
    assert url == "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()


def test_mimo_gets_reasoning_off_and_minimax_does_not():
    c, chat = critic()
    c.ask("xiaomi/mimo-v2.6-flash", PNG_1PX, "image/png", "q")
    c.ask("minimax/minimax-m3", PNG_1PX, "image/png", "q")
    assert chat.kwargs[0]["reasoning"] == {"effort": "none"}
    assert "reasoning" not in chat.kwargs[1]


def test_an_empty_reply_is_an_empty_string_not_none():
    c, chat = critic()
    chat.send = lambda **k: SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=None), finish_reason="length")])
    assert c.ask("minimax/minimax-m3", PNG_1PX, "image/png", "q") == ""
