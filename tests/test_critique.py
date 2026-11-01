"""POST /api/critique with fake generator and fake critic. No key, nothing billed."""
import json
import uuid

from fastapi.testclient import TestClient

from app import main
from app.brief import ProductBrief
from app.critique_parser import build_checklist
from tests.conftest import GOOD_BRIEF, FakeCritic

REQS = build_checklist(ProductBrief(**GOOD_BRIEF))
MAIN, SECOND = "minimax/minimax-m3", "xiaomi/mimo-v2.6-flash"


def good(unmet=()):
    checks = [{"requirement": r, "met": r not in unmet, "evidence": "seen"} for r in REQS]
    return json.dumps({"checks": checks, "problems": []})


def setup(env, replies):
    critic = FakeCritic(replies)
    main.app.dependency_overrides[main.get_critic] = lambda: critic
    from tests.conftest import FakeGenerator
    main.app.dependency_overrides[main.get_generator] = lambda: FakeGenerator()
    client = TestClient(main.app)
    image_id = client.post("/api/generate", json={"brief": GOOD_BRIEF, "variation": 1}).json()["id"]
    return client, critic, image_id


def critique(client, image_id):
    return client.post("/api/critique", json={"id": image_id})


def teardown_function():
    main.app.dependency_overrides.clear()


def test_valid_reply_returns_every_check_and_a_score_computed_in_code(env):
    client, critic, image_id = setup(env, {MAIN: [good(unmet=[REQS[1]])], SECOND: [good(unmet=[REQS[1]])]})
    body = critique(client, image_id).json()
    assert body["status"] == "ok"
    assert [c["requirement"] for c in body["checks"]] == REQS
    assert body["score"] == 9 and body["unmet"] == [REQS[1]]
    assert body["disagreements"] == []


def test_the_critic_receives_the_saved_image_not_just_the_prompt(env):
    client, critic, image_id = setup(env, {"*": [good(), good()]})
    critique(client, image_id)
    saved = client.get(f"/api/images/{image_id}").content
    assert critic.calls[0]["image"] == saved
    assert critic.calls[0]["media_type"] == "image/png"
    assert all(r in critic.calls[0]["prompt"] for r in REQS)


def test_two_bad_replies_in_a_row_are_unavailable_not_an_error(env):
    client, critic, image_id = setup(env, {MAIN: ["not json", "still not json"]})
    r = critique(client, image_id)
    assert r.status_code == 200 and r.json() == {"status": "unavailable"}
    assert [c["model"] for c in critic.calls] == [MAIN, MAIN]      # one retry, then stop


def test_one_bad_reply_then_a_good_one_is_ok_after_one_retry(env):
    client, critic, image_id = setup(env, {MAIN: ["oops", good()], SECOND: [good()]})
    assert critique(client, image_id).json()["status"] == "ok"
    assert [c["model"] for c in critic.calls] == [MAIN, MAIN, SECOND]


def test_disagreement_between_the_two_critics_is_listed_and_does_not_change_the_score(env):
    client, _, image_id = setup(env, {MAIN: [good()], SECOND: [good(unmet=[REQS[3]])]})
    body = critique(client, image_id).json()
    assert body["disagreements"] == [REQS[3]]
    assert body["score"] == 10
    assert body["second_model"] == SECOND and body["second_status"] == "ok"


def test_second_critic_unavailable_still_shows_the_first(env):
    client, _, image_id = setup(env, {MAIN: [good()], SECOND: ["x", "y"]})
    body = critique(client, image_id).json()
    assert body["status"] == "ok" and body["second_status"] == "unavailable" and body["disagreements"] == []


def test_second_critic_can_be_turned_off(env):
    env.setenv("SECOND_CRITIQUE_MODEL", "")
    client, critic, image_id = setup(env, {MAIN: [good()]})
    body = critique(client, image_id).json()
    assert body["second_status"] == "off" and [c["model"] for c in critic.calls] == [MAIN]


def test_bad_or_unknown_id_is_404(env):
    client, critic, _ = setup(env, {})
    assert critique(client, "../../app/main.py").status_code == 404
    assert critique(client, str(uuid.uuid4())).status_code == 404
    assert critic.calls == []


def test_no_key_means_503(env):
    client, _, image_id = setup(env, {})
    main.app.dependency_overrides.pop(main.get_critic)
    assert critique(client, image_id).status_code == 503
