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
