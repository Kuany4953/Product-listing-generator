# Spec: Product Listing Image Generator

**Status:** Approved (revision 2, see "Changes from revision 1")
**Author:** Kuany Kuany
**Approved by:** Abdel-Rhamane Sidally Toure, Oct 20th 2026 (revision 1). Revision 2 is approved by the reviewer of PR `week06-kuany` on GitHub.

This spec describes how we build what `intent/generate.md` and
`intent/critique.md` promise. Every acceptance criterion in those files
maps to a test listed in the "Tests" section below.

## Changes from revision 1
- **Provider:** all model calls now go through **OpenRouter** with one key (`OPENROUTER_API_KEY`), instead of OpenAI and Anthropic with two keys. The course's class key and the Week 6 lab both use OpenRouter, the lab requires the `openrouter` SDK in this repository, and one key means one usage page for the cost total.
- **Image model:** `gpt-image-1` is replaced by `black-forest-labs/flux.2-klein-4b`.
- **Critic:** the critic is `minimax/minimax-m3`, and a second, cheaper model, `xiaomi/mimo-v2.6-flash`, checks it. They replace Claude Haiku and Claude Sonnet.
- **Score:** the score is now **computed in code** from the checklist, not written by the model. Our Week 6 lab showed critics misreading images confidently, so the program does not take a number from the critic.
- **PR #2 review points (sidallytoure), now in this spec:**
  - the screener matches whole words;
  - image size is in config;
  - a failed generation counts as done for ranking and goes last;
  - image ids must be UUIDs;
  - the ranking code is its own file, `static/ranking.js`.

## Tech stack
| Part | Choice | Why |
|---|---|---|
| Back end | Python 3.12+, FastAPI | Team decision. FastAPI gives us a web server, request validation, and JSON handling with little code |
| Server | Uvicorn | Standard way to run FastAPI |
| Front end | Plain HTML, CSS, and JavaScript served by FastAPI | One page with a form and a grid; no framework needed |
| Image generation | OpenRouter Image API (`black-forest-labs/flux.2-klein-4b`) via the `openrouter` package | Cheap, fast, takes a seed, returns the image bytes |
| Vision critique | OpenRouter chat endpoint with an image part (`minimax/minimax-m3`, checked by `xiaomi/mimo-v2.6-flash`) | Both accept images; two companies' models give a second opinion |
| API wrappers | Our own small classes around the SDK (`ImageGenerator`, `ImageCritic`) | Tests swap in a fake without calling the real API |
| Tests | pytest, FastAPI `TestClient`, fakes | Unit tests for logic, `TestClient` for the HTTP endpoints |
| Browser test | Playwright for Python (`pytest-playwright`) | Drives the real page in a browser with faked API responses |
| Lint | ruff | Runs in the gate before every push and in CI |

## Dependencies
| Library | Reason | Needed by |
|---|---|---|
| `fastapi` | Routes, request validation of the brief, JSON responses | app |
| `uvicorn` | Runs the FastAPI app | app, browser tests |
| `openrouter` | Official OpenRouter SDK. It calls the Image API (`client.images.generate`) and the chat endpoint with an image part, through one client and one key | `app/generator.py`, `app/critic.py` |
| `python-dotenv` | Loads a local, git-ignored `.env` in development so the key never goes in code | `app/config.py` |
| `httpx` | Required by FastAPI's `TestClient` | tests |
| `pytest`, `pytest-playwright` | Unit tests and the browser-driven check | tests |
| `ruff` | Linter run by the gate | development |

The app dependencies are in `requirements.txt`, and the test and development ones in `requirements-dev.txt`. Nothing else is installed. The guard hook (`.claude/hooks/guard.py`) blocks installing a package this table does not name.

## Decisions and alternatives considered
For each component we record two decisions, language and model, and
the alternative we considered for each.

### Component 1: Generate (image creation)
**Language: Python.** Alternatives: Java, Node.js.
- A FastAPI endpoint takes a few lines. Java with Spring Boot needs more setup files and boilerplate for the same endpoint, and has no OpenRouter SDK, so we would hand-write the HTTP requests.
- pytest tests are plain functions, and the API client is easy to replace with a fake.
- The team is most comfortable in Python. Node.js would let us use one language for the whole app, but the team is less comfortable writing a back end in JavaScript.

**Framework: FastAPI.** Alternative: Flask.
- FastAPI checks each request against the brief rules (required fields, length limits) automatically. In Flask we would write those checks by hand.
- Image generation takes several seconds. The generate and critique routes are plain `def` functions, so FastAPI runs each one in its thread pool and 5 generations at once do not block each other. The SDK client is synchronous; calling it inside an `async def` route would block the server.

**Model: `black-forest-labs/flux.2-klein-4b`.** Alternatives: OpenAI `gpt-image-1` (revision 1's choice), `google/gemini-3.1-flash-lite-image`.
- About $0.014 per image. A demo click of 5 images costs about $0.07, compared with several times that for `gpt-image-1` at medium quality.
- It takes a seed, so we record the seed with each image and a person can regenerate the same picture.
- It returns the image bytes directly, so we save the exact bytes and critique that same file.
- Provenance: FLUX's images carry a signed C2PA manifest from Black Forest Labs, checked on real images (`README.md`, "Provenance check"). We keep it intact by saving the bytes unchanged (see "Saving images").
- `google/gemini-3.1-flash-lite-image` was tried in the Week 6 lab on the same prompt. Its cost and verdict are recorded in Kuany's `week06/CHECKS.md`.

### Component 2: Critique (vision)
**Language: Python.** Same back end, same reasons as Component 1.

**Model: `minimax/minimax-m3`, checked by `xiaomi/mimo-v2.6-flash`.** Alternatives: the Claude Haiku and Sonnet pair from revision 1, and a single critic with no second model.
- Both are class vision models. They come from different companies than FLUX and from each other, so they are less likely to share a blind spot.
- **A second critic instead of trusting one.** In the Week 6 lab, the course's critic reported a correctly spelled title as misspelled. A single critic's mistake is invisible to the program. A second model costs little (mimo is far cheaper), and where the two disagree, the page says so and tells the seller to look.
- mimo needs hidden reasoning off (`reasoning={"effort": "none"}`); minimax needs it on. This is kept in a per-model table in `critic.py`.
- **Cheap vs. strong:** see "Model comparison" for the results on real images from this project.

### Component 3: Brief validation and screening
**Language: Python** (Pydantic models in FastAPI). Alternative: validation only in the browser. That is rejected because anyone can call the API without the page.

**Model: none.** Alternative: ask a model whether a brief mentions a person or a brand. That is rejected because it costs a call per click, can be wrong without telling us, and the screening must run before any billed call. A whole-word keyword list is free, fast, and testable. Its limit is stated under "Screening briefs".

### Component 4: Storage
**Language: Python, standard library only** (files on disk). Alternative: SQLite. That is rejected because each image is one file plus one JSON sidecar and we never query across images.

**Model: none.**

### Component 5: Front end
**Language: plain HTML, CSS, and JavaScript.** Alternative: React.
- The app is one page: a form, a grid, and badges. React would add a build step and tooling without a real benefit.
- Plain JavaScript is easier for every team member to read and explain.

**Model: none.** The front end calls only our own back end. The key never reaches the browser.

### Testing tools
**Browser test: Playwright.** Alternative: Selenium.
- Playwright can fake our API responses inside the browser test, so the test never calls the paid APIs and costs nothing to run.
- It waits for elements automatically. Images appear one at a time, which makes Selenium tests flaky without hand-written waits.
- It has an official Python package and runs under pytest, like our other tests.

**Unit tests: pytest.** Alternative: Python's built-in `unittest`.
- Shorter tests, clearer failure messages, and it is the standard choice for testing FastAPI apps.

## Project layout
```
requirements.txt, requirements-dev.txt, pyproject.toml
app/
  main.py               FastAPI app and routes
  config.py             Settings read from environment variables
  brief.py              ProductBrief model and validation rules
  screener.py           Rejects briefs asking for people or brands (whole words)
  blocklist.txt         Celebrity and brand names to reject
  prompts.py            Builds the prompt for each variation
  generator.py          ImageGenerator: prompt + seed -> image bytes (OpenRouter Image API)
  store.py              Saves images with their brief and embedded provenance; UUID ids only
  critic.py             ImageCritic: image + brief -> checklist critique (two models)
  critique_parser.py    Extracts and checks the model's JSON; computes the score in code
  static/index.html, app.js, ranking.js, style.css
tests/                  Tests (see "Tests")
tests/browser/          Playwright tests for the page
images/                 The Week 6 lab image set and manifest (navy basket, five compositions)
```

## Configuration
Read from environment variables (a local `.env` file is loaded in
development):

| Setting | Default | Purpose |
|---|---|---|
| `VARIATIONS` | `5` | Number of images per brief. Set to `1` during development to save cost |
| `IMAGE_MODEL` | `black-forest-labs/flux.2-klein-4b` | Image model |
| `IMAGE_ASPECT_RATIO` | `1:1` | Image shape. With FLUX the price is per image, not per size |
| `CRITIQUE_MODEL` | `minimax/minimax-m3` | The critic |
| `SECOND_CRITIQUE_MODEL` | `xiaomi/mimo-v2.6-flash` | The model that checks the critic. Empty turns the second critic off |
| `STORAGE_DIR` | `./generated` | Where images and briefs are saved |

The API key comes only from the environment variable `OPENROUTER_API_KEY`. It is never written in code or config files. `.env` and `generated/` are listed in `.gitignore`, and `.env.example` lists the variable names with no values.

## Product brief rules
| Field | Required | Max length |
|---|---|---|
| Product name | Yes | 80 characters |
| Color | Yes | 40 |
| Material | Yes | 40 |
| Background | Yes | 80 |
| Style | No | 80 |
| Extra details | No | 300 |

- **Front end:** the Generate button stays disabled until all required fields are filled and every field is within its limit.
- **Back end:** it checks the same rules again and returns HTTP 400 with a message if a request breaks them, so the rules hold even if the UI is bypassed. Leading and trailing spaces are stripped, and a field of only spaces counts as empty.

## Screening briefs (Responsible AI)
`screener.py` runs before any API call. It rejects a brief if any
field contains, **as a whole word** (case-insensitive):
- **people:** person, people, man, men, woman, women, child, children, kid, kids, boy, girl, baby, human, model, models, hand, hands, face, faces, wearing, worn, selfie, portrait, celebrity;
- **blocklist:** a name on our blocklist of celebrities and well-known brands, stored in `app/blocklist.txt`, one name per line; a multi-word name must match as a phrase.

Whole-word matching means "Handwoven", "leather handles", "handbag", "mango" and "manual" pass, while "a man holding it" and "Nike shoes" are rejected.

A rejected brief returns HTTP 422 with the message: "This tool creates
product-only images. Please remove references to people or real
brands." No API call is made.

Every prompt also ends with: "Show only the product. No people, no
hands, no text, no logos." The checklist critique checks "No people
or hands appear in the image" on every image.

**Known limit:** a keyword list cannot catch every brand or every way
of describing a person. We note this in the README rather than claim
complete coverage.

## Generation
### Variations
`prompts.py` builds one base prompt from the brief and adds one
composition per variation, in this order:
1. Front view, centered
2. Top-down view
3. Close-up showing material texture
4. Three-quarter angled view
5. Lifestyle scene in the chosen background, no people

If `VARIATIONS` is less than 5, the first N are used. `VARIATIONS` must be between 1 and 5.

### How images appear as they finish
The page gets the variation count from `GET /api/config`, then sends
one `POST /api/generate` request per variation at the same time. Each
image shows up in its grid slot as soon as its request returns. We
generate all at once, which is faster for the seller, and one request
per image keeps failure handling simple.

### Seeds
Each generation uses a random seed. The seed is saved with the image, so a person can regenerate the same picture by hand.

### Failure and retry
- If a request fails (API error, a timeout of 90 seconds, or a safety refusal), the back end returns HTTP 502 with a short message. That slot shows "Image could not be generated" and a **Retry** button, which resends the same request for that variation only.
- Other slots are not affected.
- For ranking, a failed slot counts as finished and goes last. Ranking never waits on an image that will not arrive.

### Saving images
- **Files:** each image is saved as `generated/<id>.<ext>` next to `generated/<id>.json`. The JSON holds the brief, the variation number, the model, the seed, the media type, the cost from the reply, and a timestamp.
- **Ids:** `<id>` is a UUID4 made by the server. Every route that takes an id rejects anything that is not a UUID with HTTP 404, so `../` cannot reach other files.
- **Provenance:** FLUX.2 klein returns JPEGs that already carry a **signed C2PA manifest** (checked on real images on 2026-10-31; see `README.md`, "Provenance check"). The manifest:
  - is signed by Black Forest Labs Inc.;
  - names the generator "FLUX.2 [klein]";
  - records a `c2pa.created` action and a `c2pa.ai-disclosure` assertion.

  C2PA binds a hash of the file's bytes, so changing any byte breaks it. Therefore:
  - **When the image has a C2PA manifest** (a JUMBF box labelled `c2pa`), `store.py` saves the bytes **exactly as returned**.
  - **When it has none** (another model or provider), `store.py` writes our own unsigned label into the file: `ai_generated=true`, the model, the seed, the time, and the tool name. PNG gets `tEXt` chunks and JPEG a comment (`COM`) segment.
  - In both cases the pixels are not changed, and the JSON sidecar records the same provenance.

  The critique always loads the saved file by `id`, so it judges exactly the image the seller saw.

Every image in the UI has an "AI-generated mockup" label.

## Critique
### Flow
When an image arrives, the page sends `POST /api/critique` with the
image `id`. The back end loads the saved image and brief and builds a
**checklist** of yes/no requirements from the brief:
- "The product is a {product name}"
- "The product is {color}"
- "The product looks like it is made of {material}"
- "The background is {background}"
- "The style is {style}" (only if given)
- "No people or hands appear in the image"
- "There is no text or logo in the image"

It sends the checklist and the image (as a base64 data URL in an image content part) to the critic.

### Prompt and output format
The model is told to answer every item strictly from what is visible,
and to reply with JSON only:

```json
{
  "checks": [
    {"requirement": "The product is navy blue", "met": false, "evidence": "The basket is light brown"},
    {"requirement": "The background is plain white", "met": true, "evidence": "Plain white backdrop"}
  ],
  "problems": ["A second basket is partly visible on the right"]
}
```

`evidence` must describe what is visible in the image (e.g., the actual
color), not repeat the brief. This is how we show the critique reads
the image.

### Checking the response (in code, not by the critic)
`critique_parser.py`:
1. Extracts JSON from the reply (the first `{` to the last `}`, so fenced JSON and JSON inside prose parse).
2. Decides whether the reply is usable. A reply with no JSON, invalid JSON, or no `checks` list is **unusable**.
3. Compares the checks with the checklist:
   - a requirement the critic did not answer is reported as **missing**;
   - an item the critic answered that was not asked is reported as **invented**;
   - only a literal `met: true` counts as met.
4. **Computes the score in code:** `score = round(10 × met / number of requirements)`, minus 1 for each item in `problems` (at most 3), floored at 0. A missing requirement counts as not met.

If the critic's reply is unusable, the back end asks once more. If the
second answer is also unusable, the endpoint returns
`{"status": "unavailable"}` and the page shows "Critique unavailable"
under that image. The page never crashes.

### Second critic
If `SECOND_CRITIQUE_MODEL` is set, the same checklist and image go to the second model, also with one retry. The response lists every requirement where the two critics disagree. The page shows "Critics disagree on: … (look at the image yourself)" under that image. The score shown is the first critic's, and a disagreement never changes it silently. If the second critic is unavailable, the first critic's result is still shown.

### Ranking
`static/ranking.js` sorts the results when every slot is finished, meaning critiqued, "Critique unavailable", or generation failed:
- by score, highest first;
- images without a score go last;
- equal scores keep their original variation order (JavaScript's sort is stable).

The first image gets a "Top pick" badge.

The critique panel is labeled: "AI critique: checks the image against
your brief only and may be wrong."

### Model comparison (cheap vs. strong, on a real task)
The task is to critique the Week 6 lab's five navy-basket images, which are real FLUX output for this project's own prompt family, plus one deliberately wrong test brief. The checklist and the code checker are the same for both models. The cheaper model is `xiaomi/mimo-v2.6-flash`, the stronger one is `minimax/minimax-m3`, and per-critique cost comes from `usage.cost`.

Results: **filled in from the run recorded in Kuany's `week06/CHECKS.md`, see the table below.**

| Model | Images ok / 5 | Wrong-brief mistakes caught | JSON failures | Cost per critique | Seconds per critique |
|---|---|---|---|---|---|
| `xiaomi/mimo-v2.6-flash` (cheap) | | | | | |
| `minimax/minimax-m3` (stronger) | | | | | |

**Decision:** minimax is the critic and mimo the checker, unless the results show mimo catches as much, in which case we would swap them to save cost.

## API endpoints
| Method and path | Body | Returns |
|---|---|---|
| `GET /api/config` | none | `{ "variations": 5 }` |
| `POST /api/generate` | `{ brief, variation }` | `{ id, imageUrl }`; 400 bad brief or variation; 422 screened out; 502 generation failed |
| `GET /api/images/{id}` | none | The saved image; 404 if `id` is not a UUID or does not exist |
| `POST /api/critique` | `{ id }` | `{ status: "ok", checks, problems, score, missing, invented, disagreements }` or `{ "status": "unavailable" }`; 404 for a bad id |

## Cost
Each click of Generate costs `VARIATIONS` image generations (about $0.014 each on FLUX) plus `VARIATIONS` critiques on each of the two critics (and up to that many again if critiques need a retry). With the default of 5, one click is about $0.10. During development we keep `VARIATIONS=1`. Real per-image and per-critique costs from the OpenRouter Activity page go in the README's cost section.

## Tests
Each test maps to an acceptance criterion in the intent files. All
tests use a fake `ImageGenerator` and a fake `ImageCritic`, so
they never call the real APIs or need API keys. Browser tests use
Playwright's request interception to fake `/api/generate`, `/api/images`
and `/api/critique` responses.

| Intent criterion | Test |
|---|---|
| Valid brief displays 5 images | `test_generate.py`: with `VARIATIONS=5`, `/api/config` returns 5, and 5 generate calls each return an image. `tests/browser/test_page.py`: filling the form and clicking Generate shows 5 images |
| Required field empty is blocked | `test_brief.py`: a missing or blank required field fails validation, and the endpoint returns 400. `tests/browser/test_page.py`: with a required field empty, the Generate button is disabled |
| Brief with a person or real brand is rejected | `test_screener.py`: briefs mentioning a person or a blocklisted brand are rejected and the generator is never called; "Handwoven … leather handles" passes |
| One failure, others still display | `test_generate.py`: the fake generator fails for variation 3 only; variations 1, 2, 4, 5 still succeed. `tests/browser/test_page.py`: slot 3 shows an error and a Retry button, and the other 4 show images |
| Variation setting 1 gives exactly 1 image | `test_generate.py`: with `VARIATIONS=1`, `/api/config` returns 1 and only 1 prompt is built |
| No API key in committed files | `test_no_keys.py`: scans every tracked file for key patterns (`sk-or-`, `sk-`) and fails if any are found; runs in the gate and in CI |
| Each image gets a score and checklist | `test_critique.py`: a valid fake response returns all checks and a score computed in code |
| Wrong-color test image marked "does not match" | `test_critic_live.py` (marked `live`, uses the real API, skipped without a key): a navy-blue brief checked against a lab image with the color requirement changed to red returns that requirement unmet |
| Sorted by score, highest is "Top pick" | `tests/browser/test_page.py`: with faked critique scores, the page puts the highest first, keeps order on ties, puts unavailable and failed slots last, and labels the first "Top pick" |
| Malformed response shows "Critique unavailable" | `test_critique_parser.py` and `test_critique.py`: two bad responses in a row return `status: "unavailable"` with no exception |
| Vision request contains image data | `test_critic.py`: a fake OpenRouter client captures the request and checks it has an `image_url` part with a base64 data URL of the saved file |

Also tested: the score is computed in code and ignores any `score` the model sends; missing and invented requirements are reported; a non-UUID id returns 404; provenance metadata is present in a saved PNG and JPEG; disagreements between two critics are listed.

## Out of scope
Same as the intent files: no editing images, no uploading the seller's
own photo, no posting to marketplaces, no automatic regeneration, no
sales predictions.
