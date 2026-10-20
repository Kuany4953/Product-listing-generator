# Plan: Product Listing Image Generator

**Author:** Kuany Kuany
**Based on:** `intent/generate.md`, `intent/critique.md`, `spec.md`

This plan lists the files we build, the order we build them in, who
owns each part, the risks, and how we prove each part works.

## Owners
| Member | GitHub | Owns |
|---|---|---|
| Kuany Kuany | Kuany4953 | Project skeleton, brief form, validation, screening |
| Jeevan Gowda Kumaraswamy | jeevgowda | Image generation, saving, image grid and retry |
| Abdel-Rhamane Sidally Toure | sidallytoure | Critique, response parsing, ranking and "Top pick" |

Each owner opens at least one pull request for their part, and a
different member reviews it. Every feature PR also adds
`reviews/<branch-name>/REVIEW.md`, written by a separate reviewing
agent (a fresh Claude session given only the PR's diff).

## Order

### Step 0: Skeleton (Kuany, first, by Oct 21)
Everyone else builds on this, so it merges first.

| File | Purpose |
|---|---|
| `requirements.txt` | fastapi, uvicorn, openai, anthropic, python-dotenv, pytest, pytest-playwright |
| `app/main.py` | FastAPI app, serves `static/`, `GET /api/config`, empty stubs for the other routes |
| `app/config.py` | Reads `VARIATIONS`, `CRITIQUE_MODEL`, `STORAGE_DIR`, API keys from the environment |
| `app/static/index.html`, `app.js`, `style.css` | Page shell with empty form, grid, and critique areas; `app.js` has one marked section per owner |
| `tests/conftest.py` | Shared `FakeGenerator` and `FakeCritic` used by all tests |
| `tests/test_config.py` | Smoke test: `/api/config` returns the variation count |
| `.env.example` | Variable names with no values |
| `.github/workflows/ci.yml` | Runs pytest and the API key scan on every PR |

**Proof:** `pytest` passes locally and in CI; `uvicorn app.main:app`
serves the empty page.

### Step 1: Features, in parallel (Oct 21–24)
The interfaces are fixed in `spec.md`, and the fakes from Step 0 stand
in for the other parts, so all three can work at the same time.

**1a. Brief and screening (Kuany)**
| File | Purpose |
|---|---|
| `app/brief.py` | `ProductBrief` with required fields and length limits |
| `app/screener.py`, `app/blocklist.txt` | Rejects people, celebrities, and brands (HTTP 422) |
| `app/static/app.js` (form section) | Disables Generate until the brief is valid |
| `tests/test_brief.py`, `tests/test_screener.py` | Validation and screening tests |

**Proof:** tests for "required field empty is blocked" and "person or
brand is rejected" pass, and the screener test shows the generator is
never called.

**1b. Generation (Jeevan)**
| File | Purpose |
|---|---|
| `app/prompts.py` | Base prompt plus the 5 compositions |
| `app/generator.py` | Calls `gpt-image-1`, returns image bytes |
| `app/store.py` | Saves `<id>.png` and `<id>.json` unchanged |
| `app/main.py` | `POST /api/generate`, `GET /api/images/{id}` |
| `app/static/app.js` (grid section) | One request per variation, "AI-generated mockup" label, error and Retry per slot |
| `tests/test_generate.py` | 5 images, 1 image, one failure with others still shown |

**Proof:** generate tests pass; one real run with `VARIATIONS=1`
saves an image.

**1c. Critique (Abdel-Rhamane)**
| File | Purpose |
|---|---|
| `app/critic.py` | Sends saved image (base64) and brief to Claude |
| `app/critique_parser.py` | Checks the JSON; one retry, then "unavailable" |
| `app/main.py` | `POST /api/critique` |
| `app/static/app.js` (critique section) | Checklist and score under each image, ranking, "Top pick" badge, AI disclaimer |
| `tests/test_critic.py`, `tests/test_critique_parser.py`, `tests/test_critique.py` | Image data is sent, malformed responses handled, fields present |
| `tests/images/` | Test images, including a red basket for a navy brief |
| `tests/test_critic_live.py` | Real API check that the red image fails on color (marked `live`, not in CI) |

**Proof:** critique tests pass; the live test marks the wrong-color
image "does not match."

### Step 2: Browser tests and reviews (Oct 25)
| File | Owner | Checks |
|---|---|---|
| `tests/browser/test_page.py` | Kuany | Generate is disabled with a required field empty |
| | Jeevan | 5 images appear; a failed slot shows Retry while the others display |
| | Abdel-Rhamane | Images sorted by score, ties keep order, first is "Top pick" |

All feature PRs reviewed, `REVIEW.md` added, and merged.

**Proof:** `pytest` (unit and browser) passes in CI on `main`.
**Due Oct 26:** tests that run, browser check, one reviewed PR per member.

### Step 3: Evidence and documents (Oct 27–31)
| Task | Owner | Proof |
|---|---|---|
| Model comparison: Haiku 5.5 vs Sonnet 5.5 on 10+ real images, results written into `spec.md`, `CRITIQUE_MODEL` set | Abdel-Rhamane | Results table in `spec.md` |
| C2PA check on a saved image | Jeevan | Tool output or screenshot noted in `README.md` |
| `README.md`: how to run, running cost total from both usage pages | Kuany | Cost section with dates and amounts |
| `CLAUDE.md`: how to run, test, and the project rules | Kuany | File matches the code |
| `ANNOTATION.md`: four questions for each component, including one confidently wrong agent output we corrected | Each owner, for their part | One section per component |

### Step 4: Submit (Nov 1–2)
- Full run-through of the live demo with `VARIATIONS=5`.
- Everyone reads every file so each of us can explain all of it.
- Tag the final commit `tp1-submitted`, push the tag, submit the repo
  URL on Moodle by Nov 2, 1:30 PM.

## Risks
| Risk | Effect | What we do |
|---|---|---|
| API cost grows during testing | Over budget | `VARIATIONS=1` in development; tests use fakes; check usage pages weekly and update `README.md` |
| API key committed | Key counts as compromised | `.env` in `.gitignore`; CI key scan; if it happens, revoke the key immediately |
| Three people editing `app.js` and `main.py` | Merge conflicts | Skeleton gives each owner a marked section and route stub; pull `main` before starting; keep PRs small |
| Image generation slow or times out | Empty slots in the demo | 60-second timeout per image and a Retry button |
| Claude returns malformed JSON | Page breaks | Parser with one retry, then "Critique unavailable" |
| Keyword screener misses a brand or person | Responsible AI gap | OpenAI's safety filter as backup; limit stated in `README.md` |
| Model names or prices change | Spec out of date | Check provider docs at Step 3 and update `spec.md` |
| Network fails during the live demo | App can't generate | Test the classroom network beforehand; use a phone hotspot as backup |
| A member can't explain a part | Lost credit in the defense | Cross-review every PR; walk through all code together in Step 4 |
