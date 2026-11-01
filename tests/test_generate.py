from fastapi.testclient import TestClient

from app import main
from tests.conftest import GOOD_BRIEF, PNG_1PX, FakeGenerator


def post(client, variation, brief=GOOD_BRIEF):
    return client.post("/api/generate", json={"brief": brief, "variation": variation})


def with_generator(generator):
    main.app.dependency_overrides[main.get_generator] = lambda: generator
    return TestClient(main.app)


def test_five_variations_each_return_an_image(client, generator):
    assert client.get("/api/config").json() == {"variations": 5}
    for v in range(1, 6):
        r = post(client, v)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["imageUrl"] == f"/api/images/{body['id']}"
        img = client.get(body["imageUrl"])
        assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert len(generator.calls) == 5
    assert len({c["prompt"] for c in generator.calls}) == 5         # five different compositions


def test_variations_1_gives_one_image_and_rejects_variation_2(client, env, generator):
    env.setenv("VARIATIONS", "1")
    assert client.get("/api/config").json() == {"variations": 1}
    assert post(client, 1).status_code == 200
    assert post(client, 2).status_code == 400
    assert len(generator.calls) == 1


def test_one_failure_does_not_stop_the_others(env):
    try:
        client = with_generator(FakeGenerator(fail_on=["Close-up"]))   # variation 3 only
        codes = [post(client, v).status_code for v in range(1, 6)]
    finally:
        main.app.dependency_overrides.clear()
    assert codes == [200, 200, 502, 200, 200]


def test_a_generation_failure_returns_a_short_message_not_the_exception(env):
    try:
        r = post(with_generator(FakeGenerator(fail_on=["Front view"])), 1)
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 502
    assert r.json() == {"detail": "Image could not be generated"}


def test_no_key_means_503_and_no_call(env):
    r = post(TestClient(main.app), 1)
    assert r.status_code == 503
    assert "OPENROUTER_API_KEY" in r.json()["detail"]


def test_the_record_keeps_brief_variation_model_seed_and_cost(client):
    body = post(client, 2).json()
    record = main.store.load(main.get_settings().storage_dir, body["id"])[2]
    assert record["brief"]["color"] == "Navy blue"
    assert record["variation"] == 2
    assert record["model"] == "fake/image" and record["cost"] == 0.014
    assert isinstance(record["seed"], int) and record["media_type"] == "image/png" and record["created"]


def test_saved_image_is_the_generated_image_plus_provenance(client):
    body = post(client, 1).json()
    saved = client.get(body["imageUrl"]).content
    assert saved.startswith(PNG_1PX[:33])           # signature and IHDR untouched
    assert b"ai_generated" in saved
