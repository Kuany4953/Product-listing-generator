"""Browser-driven checks of the page. Every /api call is faked; nothing is billed."""
import json

from playwright.sync_api import Page, expect

from tests.conftest import PNG_1PX

FIELDS = {"#product_name": "Handwoven storage basket", "#color": "Navy blue",
          "#material": "Seagrass", "#background": "Plain white"}


def fake_config(page: Page, variations: int = 5):
    page.route("**/api/config", lambda r: r.fulfill(json={"variations": variations}))


def fill_required(page: Page):
    for sel, value in FIELDS.items():
        page.fill(sel, value)


def test_generate_is_disabled_until_every_required_field_is_filled(page: Page, server_url):
    fake_config(page)
    page.goto(server_url)
    button = page.locator("#generate")
    expect(button).to_be_disabled()
    fill_required(page)
    expect(button).to_be_enabled()
    page.fill("#material", "")
    expect(button).to_be_disabled()
    page.fill("#material", "   ")
    expect(button).to_be_disabled()


def test_generate_is_disabled_when_a_field_is_over_its_limit(page: Page, server_url):
    fake_config(page)
    page.goto(server_url)
    fill_required(page)
    page.evaluate("document.querySelector('#color').removeAttribute('maxlength')")
    page.fill("#color", "a" * 41)
    expect(page.locator("#generate")).to_be_disabled()


def test_a_screened_brief_shows_the_servers_message(page: Page, server_url):
    fake_config(page)
    message = "This tool creates product-only images. Please remove references to people or real brands."
    page.route("**/api/generate", lambda r: r.fulfill(status=422, body=json.dumps({"detail": message}),
                                                      content_type="application/json"))
    page.goto(server_url)
    fill_required(page)
    page.fill("#extra_details", "A man holding it")
    page.click("#generate")
    expect(page.locator("#form-error")).to_have_text(message)


def fake_generate(page: Page, fail_variations=()):
    """Fake /api/generate: variation N gets id-N; listed variations fail with 502. Images are a 1px PNG."""
    def handle(route):
        v = json.loads(route.request.post_data)["variation"]
        if v in fail_variations:
            route.fulfill(status=502, json={"detail": "Image could not be generated"})
        else:
            route.fulfill(json={"id": f"id-{v}", "imageUrl": f"/api/img-fake/id-{v}"})
    page.route("**/api/generate", handle)
    page.route("**/api/img-fake/*", lambda r: r.fulfill(body=PNG_1PX, content_type="image/png"))


def test_valid_brief_shows_five_labeled_images(page: Page, server_url):
    fake_config(page)
    fake_generate(page)
    page.goto(server_url)
    fill_required(page)
    page.click("#generate")
    expect(page.locator(".slot img")).to_have_count(5)
    expect(page.locator(".slot .badge.ai")).to_have_count(5)
    expect(page.locator(".slot .badge.ai").first).to_have_text("AI-generated mockup")


def test_one_failed_slot_shows_retry_and_the_others_display(page: Page, server_url):
    fake_config(page)
    fake_generate(page, fail_variations={3})
    page.goto(server_url)
    fill_required(page)
    page.click("#generate")
    expect(page.locator(".slot img")).to_have_count(4)
    failed = page.locator(".slot[data-variation='3']")
    expect(failed.locator(".error")).to_have_text("Image could not be generated")
    page.unroute("**/api/generate")
    fake_generate(page)
    failed.locator("button.retry").click()
    expect(page.locator(".slot img")).to_have_count(5)


def fake_critiques(page: Page, by_variation: dict):
    """Fake /api/critique: id-N gets by_variation[N] (a score, or None for unavailable)."""
    def handle(route):
        v = int(json.loads(route.request.post_data)["id"].split("-")[1])
        score = by_variation.get(v)
        if score is None:
            route.fulfill(json={"status": "unavailable"})
            return
        checks = [{"requirement": "The product is Navy blue", "met": score >= 5,
                   "evidence": "Deep navy weave"}]
        route.fulfill(json={"status": "ok", "score": score, "checks": checks, "problems": [],
                            "missing": [], "invented": [], "unmet": [],
                            "disagreements": ["The product is Navy blue"] if v == 1 else [],
                            "second_model": "xiaomi/mimo-v2.6-flash", "second_status": "ok"})
    page.route("**/api/critique", handle)


def order(page: Page):
    return [int(v) for v in page.locator(".slot").evaluate_all("els => els.map(e => e.dataset.variation)")]


def test_ranked_by_score_ties_keep_order_unavailable_last_top_pick(page: Page, server_url):
    fake_config(page)
    fake_generate(page)
    fake_critiques(page, {1: 6, 2: 9, 3: None, 4: 9, 5: 3})
    page.goto(server_url)
    fill_required(page)
    page.click("#generate")
    expect(page.locator(".slot.top-pick")).to_have_count(1)
    assert order(page) == [2, 4, 1, 5, 3]
    expect(page.locator(".slot.top-pick .badge.pick")).to_have_text("Top pick")
    expect(page.locator(".slot[data-variation='3'] .critique")).to_contain_text("Critique unavailable")
    expect(page.locator("#disclaimer")).to_be_visible()
    expect(page.locator("#disclaimer")).to_have_text(
        "AI critique: checks the image against your brief only and may be wrong.")


def test_failed_generation_counts_as_finished_and_goes_last(page: Page, server_url):
    fake_config(page)
    fake_generate(page, fail_variations={2})
    fake_critiques(page, {1: 4, 3: 8, 4: 8, 5: 7})
    page.goto(server_url)
    fill_required(page)
    page.click("#generate")
    expect(page.locator(".slot.top-pick")).to_have_count(1)
    assert order(page) == [3, 4, 5, 1, 2]


def test_checklist_score_and_disagreement_are_shown(page: Page, server_url):
    fake_config(page, variations=1)
    fake_generate(page)
    fake_critiques(page, {1: 9})
    page.goto(server_url)
    fill_required(page)
    page.click("#generate")
    slot = page.locator(".slot[data-variation='1']")
    expect(slot.locator(".score")).to_have_text("Score 9/10")
    expect(slot.locator(".checks li.met")).to_contain_text("The product is Navy blue")
    expect(slot.locator(".checks .evidence")).to_have_text("Deep navy weave")
    expect(slot.locator(".disagree")).to_contain_text("Critics disagree on: The product is Navy blue")
