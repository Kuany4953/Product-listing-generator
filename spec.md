# Spec: Product Listing Image Generator

**Status:** Draft (pending review)
**Author:** Kuany Kuany
**Approved by:**  Abdel-Rhamane Sidally Toure, Oct 20th 2026

This spec describes how we build what `intent/generate.md` and
`intent/critique.md` promise. Every acceptance criterion in those files
maps to a test listed in the "Tests" section below.

## Tech stack
| Part | Choice | Why |
|---|---|---|
| Back end | Python 3.12, FastAPI | Team decision; FastAPI gives us a web server, request validation, and JSON handling with little code |
| Server | Uvicorn | Standard way to run FastAPI |
| Front end | Plain HTML, CSS, and JavaScript served by FastAPI | One page with a form and a grid; no framework needed |
| Image generation | OpenAI Images API (`gpt-image-1`) via the `openai` package | Good at product shots; returns image data directly |
| Vision critique | Claude via the `anthropic` package; see "Model comparison" | Accepts image input and can return structured JSON |
| API wrappers | Our own small classes around each SDK | Lets tests swap in a fake without calling the real API |
| Tests | pytest, FastAPI `TestClient`, `unittest.mock` | Unit tests for logic, `TestClient` for the HTTP endpoints |

## Project layout
```
requirements.txt
app/
  main.py               FastAPI app and routes
  config.py             Settings read from environment variables
  brief.py              ProductBrief model and validation rules
  screener.py           Rejects briefs asking for people or brands
  prompts.py            Builds the prompt for each variation
  generator.py          ImageGenerator: brief + variation -> image bytes (OpenAI)
  critic.py             ImageCritic: image bytes + brief -> critique (Claude)
  critique_parser.py    Parses and checks the model's JSON
  store.py              Saves images with their brief
  blocklist.txt         Celebrity and brand names to reject
  static/index.html, app.js, style.css
tests/                  Tests (see "Tests")
tests/images/           Fixed test images (e.g., wrong color)
```

## Configuration
Read from environment variables (a local `.env` file is loaded in
development):

| Setting | Default | Purpose |
|---|---|---|
| `VARIATIONS` | `5` | Number of images per brief. Set to `1` during development to save cost |
| `CRITIQUE_MODEL` | Decided by the model comparison | Which Claude model critiques images |
| `STORAGE_DIR` | `./generated` | Where images and briefs are saved |

API keys come only from environment variables `OPENAI_API_KEY` and
`ANTHROPIC_API_KEY`. They are never written in code or config files.
`.env` and `generated/` are listed in `.gitignore`.

## Product brief rules
| Field | Required | Max length |
|---|---|---|
| Product name | Yes | 80 characters |
| Color | Yes | 40 |
| Material | Yes | 40 |
| Background | Yes | 80 |
| Style | No | 80 |
| Extra details | No | 300 |

- The front end disables the Generate button until all required fields
  are filled and every field is within its limit.
- The back end checks the same rules again and returns HTTP 400 with a
  message if a request breaks them, so the rules hold even if the UI
  is bypassed.

## Screening briefs (Responsible AI)
`screener.py` runs before any API call. It rejects a brief if any
field mentions:
- people (e.g., "person", "model", "woman", "man", "child", "hand",
  "face", "wearing"), or
- a name on our blocklist of celebrities or well-known brands
  (stored in `app/blocklist.txt`).

A rejected brief returns HTTP 422 with the message: "This tool creates
product-only images. Please remove references to people or real
brands." No API call is made.

Every prompt also ends with: "Show only the product. No people, no
hands, no text, no logos." The OpenAI API's own safety filter applies
on top of this.

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

If `VARIATIONS` is less than 5, the first N are used.

### How images appear as they finish
The page gets the variation count from `GET /api/config`, then sends
one `POST /api/generate` request per variation at the same time. Each
image shows up in its grid slot as soon as its request returns. This
answers the open question in `generate.md`: we generate all at once,
which is faster for the seller, and one request per image keeps
failure handling simple.

### Failure and retry
- If a request fails (API error, timeout of 60 seconds, or safety
  rejection), that slot shows "Image could not be generated" and a
  **Retry** button. Retry resends the same request for that variation
  only.
- Other slots are not affected.

### Saving images
Each image is saved unchanged as `generated/<id>.png` next to
`generated/<id>.json`, which holds the brief, the variation number, and
a timestamp. We save the exact bytes the API returned, so any provenance
metadata the API includes (such as C2PA) is kept. The critique always
loads the saved file by `id`, so it judges exactly the image the seller
saw.

Every image in the UI has an "AI-generated mockup" label.

## Critique
### Flow
When an image arrives, the page sends `POST /api/critique` with the
image `id`. The back end loads the saved image and brief, then sends
both to Claude: the image as base64 image data, and the brief as text.

### Prompt and output format
The model is told to compare the image to each brief field, describe
what it actually sees, and reply with JSON only:

```json
{
  "color":      { "match": false, "reason": "Basket is light brown, not navy blue" },
  "material":   { "match": true,  "reason": "Woven seagrass texture visible" },
  "background": { "match": false, "reason": "Background is light gray, not white" },
  "style":      { "match": true,  "reason": "Soft natural lighting" },
  "problems":   ["Extra basket in the corner"],
  "score": 4
}
```

- `style` is `null` if the brief had no style.
- `reason` must describe what is visible in the image (e.g., the actual
  color), not just repeat the brief. This is how we show the critique
  reads the image.

### Checking the response
`critique_parser.py` accepts the response only if it is valid JSON with all
required fields and `score` is a whole number from 0 to 10. If not, the
back end asks the model once more. If the second answer also fails, the
endpoint returns `{"status": "unavailable"}` and the page shows
"Critique unavailable" under that image. The page never crashes.

### Ranking
When every image has a critique (or "Critique unavailable"), the page
sorts images by score, highest first. Images without a score go last.
Equal scores keep their original variation order (JavaScript's sort is stable). The
first image gets a "Top pick" badge.

The critique panel is labeled: "AI critique: checks the image against
your brief only and may be wrong."

### Model comparison
Before the demo we run the critique with a cheaper model
(`claude-haiku-5-5`) and a stronger model (`claude-sonnet-5-5`) on the
same set of at least 10 real generated images, including our
deliberately wrong test images. We record, for each model:
- how many color, material, and background mistakes it catches,
- how often its JSON fails to parse,
- cost and time per critique.

We pick the model that catches the test-image mistakes reliably at the
lowest cost, set it as `CRITIQUE_MODEL`, and write the results in
this section.

## API endpoints
| Method and path | Body | Returns |
|---|---|---|
| `GET /api/config` | none | `{ "variations": 5 }` |
| `POST /api/generate` | `{ brief, variation }` | `{ id, imageUrl }`; 400 bad brief; 422 screened out; 502 generation failed |
| `GET /api/images/{id}` | none | The saved PNG |
| `POST /api/critique` | `{ id }` | Critique JSON with `status: "ok"`, or `{ "status": "unavailable" }` |

## Cost
Each click of Generate costs `VARIATIONS` image generations plus
`VARIATIONS` critiques (and up to that many again if critiques need
a retry). With the default of 5, that is 5 images and 5 to 10 vision
calls. During development we keep `VARIATIONS=1`. We will record
real per-image and per-critique costs from our API dashboards in the
README's cost section.

## Tests
Each test maps to an acceptance criterion in the intent files. All
tests use fake `ImageGenerator` and `ImageCritic` objects, so
they never call the real APIs or need API keys.

| Intent criterion | Test |
|---|---|
| Valid brief displays 5 images | `test_generate.py`: with `VARIATIONS=5`, `/api/config` returns 5, and 5 generate calls each return an image |
| Required field empty is blocked | `test_brief.py`: missing required field fails validation; `test_generate.py`: endpoint returns 400. UI button disabling is checked by hand and listed in the demo checklist |
| Brief with a person or real brand is rejected | `test_screener.py`: briefs mentioning a person or a blocklisted brand are rejected, and the generator is never called |
| One failure, others still display | `test_generate.py`: fake generator fails for variation 3 only; variations 1, 2, 4, 5 still succeed |
| Variation setting 1 gives exactly 1 image | `test_generate.py`: with `VARIATIONS=1`, `/api/config` returns 1 and only 1 prompt is built |
| No API key in committed files | CI step scans the repo for key patterns (e.g., `sk-`) and fails if any are found |
| Each image gets a score and checklist | `test_critique.py`: valid fake response returns all fields and a score |
| Wrong-color test image marked "does not match" | `test_critic_live.py` (marked `live`, uses the real API, not run in CI): the navy-brief test image that is actually red returns `color.match = false` |
| Sorted by score, highest is "Top pick" | `tests/ranking.test.js` (run with `node --test`): ranking puts highest first, keeps order on ties, puts unavailable last |
| Malformed response shows "Critique unavailable" | `test_critique_parser.py` and `test_critique.py`: two bad responses in a row return `status: "unavailable"` with no exception |
| Vision request contains image data | `test_critic.py`: a mocked Anthropic client captures the request and checks it has an image block with base64 data |

## Out of scope
Same as the intent files: no editing images, no uploading the seller's
own photo, no posting to marketplaces, no automatic regeneration, no
sales predictions.
