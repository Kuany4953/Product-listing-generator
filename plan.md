# Plan: Product Listing Image Generator

**Author:** Kuany Kuany
**Based on:** `intent/generate.md`, `intent/critique.md`, `spec.md` (revision 2)
**Approved by:** the reviewer of PR `week06-kuany` on GitHub

This plan lists the files we build, the order we build them in, who
owns each part, the risks, and how we prove each part works.

## What changed from the first plan (Oct 20)
The first plan had the skeleton on Oct 21 and features by Oct 24. None of that code was written by then, so the build moved into the Week 6 lab weekend (Oct 31 – Nov 1). Each member's Week 6 lab pull request is that member's feature PR. The provider also changed from OpenAI and Anthropic to OpenRouter (spec.md, "Changes from revision 1"). The old per-branch `reviews/<branch>/REVIEW.md` idea is replaced by the course's process: one `REVIEW.md` policy at the root, and the reviewing agent's findings posted as a comment on each PR.

## Owners and branches
| Member | GitHub | Branch | Owns |
|---|---|---|---|
| Kuany Kuany | Kuany4953 | `week06-kuany` | Spec revision 2, skeleton, config, brief form and validation, screening, gate, guard, CI, the lab image set, docs |
| Jeevan Gowda Kumaraswamy | jeevgowda | `week06-jeevan` | Prompts, image generation, storage with provenance, `/api/generate` and `/api/images`, image grid and Retry |
| Abdel-Rhamane Sidally Toure | sidallytoure | `week06-sidally` | Critic (two models), response checking and score in code, `/api/critique`, critique panel, ranking and "Top pick" |

## How every change gets in
1. **Branch:** work on your own `week06-<name>` branch, tests first.
2. **Push:** `git push` runs the gate (`.git/hooks/pre-push`, a copy of `gate.sh`): `ruff check .` and the no-key tests. A failing gate stops the push.
3. **Review:** open the PR, then run the reviewing agent from the repository root: `python3 path/to/ai-integration-course/examples/pr-review/review.py > review.txt`. It reads `REVIEW.md`, `spec.md` and the diff. Post the result with `gh pr comment --body-file review.txt`.
4. **Fix or answer:** fix every pass-1 and pass-2 finding, or reply on the PR saying why it is wrong. Rerun the reviewer until it exits 0.
5. **Merge:** a different team member reads the diff, the findings and the replies, approves on GitHub, and only then is the PR merged.

The three branches are stacked: `week06-jeevan` builds on `week06-kuany`, and `week06-sidally` builds on `week06-jeevan`. They merge in that order.

## Order

### Step 1: Skeleton, brief and screening (Kuany, `week06-kuany`)
| File | Purpose |
|---|---|
| `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` | Dependencies named in spec.md; pytest and ruff settings |
| `app/config.py` | Reads the settings in spec.md "Configuration" from the environment |
| `app/brief.py` | `ProductBrief` with required fields, length limits, blank-as-empty |
| `app/screener.py`, `app/blocklist.txt` | Whole-word people and brand screening |
| `app/main.py` | `GET /api/config`; `POST /api/generate` validates and screens, then calls the generator dependency; the generator and critic are FastAPI dependencies so tests can replace them |
| `app/static/index.html`, `app.js`, `style.css` | The page: form, grid, critique areas; the Generate button is disabled until the brief is valid |
| `tests/conftest.py` | `FakeGenerator`, `FakeCritic`, and a `client` fixture |
| `tests/test_config.py`, `test_brief.py`, `test_screener.py`, `test_no_keys.py` | Config, validation, screening, key scan |
| `tests/browser/conftest.py`, `tests/browser/test_page.py` | Starts the app on a local port; required-field check |
| `.claude/hooks/guard.py`, `.claude/settings.json` | The Week 5 guard |
| `.github/workflows/gate.yml` | Same gate in CI |
| `REVIEW.md`, `CLAUDE.md`, `README.md`, `ANNOTATION.md`, `.env.example` | Review policy, agent rules, how to run and cost, annotation |
| `images/` | Kuany's Week 6 image set and manifest |

**Proof:** the no-key tests and the browser test pass; `uvicorn app.main:app` serves the page; a brief with "Handwoven … leather handles" passes and "a man holding it" is rejected with no generator call.

### Step 2: Generation (Jeevan, `week06-jeevan`)
| File | Purpose |
|---|---|
| `app/prompts.py` | Base prompt plus the 5 compositions |
| `app/generator.py` | `OpenRouterGenerator`: one Image API call, random seed, 90 s timeout |
| `app/store.py` | UUID ids, saves image and JSON sidecar, embeds provenance (PNG `tEXt` or JPEG `COM`) |
| `app/main.py` | `POST /api/generate` wired to the generator and store; `GET /api/images/{id}` |
| `app/static/app.js` (grid section) | One request per variation, "AI-generated mockup" label, error and Retry per slot |
| `tests/test_prompts.py`, `test_generate.py`, `test_store.py` | Prompts, 5 and 1 images, one failure, UUID checks, provenance present |
| `tests/browser/test_page.py` | 5 images appear; a failed slot shows Retry while the others display |

**Proof:** tests pass; one real run with `VARIATIONS=1` saves an image whose metadata shows `ai_generated`.

### Step 3: Critique (Abdel-Rhamane, `week06-sidally`)
| File | Purpose |
|---|---|
| `app/critic.py` | `OpenRouterCritic`: checklist from brief, image as a data URL, two models, one retry each |
| `app/critique_parser.py` | JSON extraction, missing and invented requirements, score in code, disagreements |
| `app/main.py` | `POST /api/critique` |
| `app/static/ranking.js`, `app.js` (critique section) | Checklist and score under each image, disagreements, ranking, "Top pick", AI disclaimer |
| `tests/test_critic.py`, `test_critique_parser.py`, `test_critique.py` | Image data is sent, malformed replies handled, score computed in code |
| `tests/test_critic_live.py` | Real API: wrong-color brief is marked unmet (marked `live`, skipped without a key) |
| `tests/browser/test_page.py` | Sorted by score, ties keep order, unavailable and failed slots last, "Top pick" |

**Proof:** critique tests pass; the live test marks the wrong-color requirement unmet; the model comparison table in spec.md is filled in.

### Step 4: Submit (Nov 1–2)
- Full run-through of the live demo with `VARIATIONS=5`.
- Everyone reads every file, so each of us can explain all of it.
- Update `README.md` cost total from the OpenRouter Activity page.
- After all three PRs merge: tag `main` as `tp1-submitted`, push the tag, submit the repo URL on Moodle by Nov 2, 1:30 PM.

## Risks
| Risk | Effect | What we do |
|---|---|---|
| API cost grows during testing | Over budget | `VARIATIONS=1` in development; tests use fakes; the gate removes the key; README cost updated from the Activity page |
| API key committed | Key counts as compromised | `.env` in `.gitignore`; `test_no_keys.py` in the gate and CI; if it happens, revoke the key immediately |
| API key expires or runs out of credit | Nothing generates in the demo | Check with one `VARIATIONS=1` run the morning of Nov 2; backup screenshots and a recorded run |
| Stacked branches conflict | Merge pain on `main.py` and `app.js` | `main.py` has one marked block per route; `app.js` one marked section per owner; merge in order Kuany, Jeevan, Sidally |
| Image generation slow or times out | Empty slots in the demo | 90 s timeout per image and a Retry button |
| Critic returns malformed JSON | Page breaks | Parser with one retry, then "Critique unavailable" |
| Critic confidently wrong | Seller trusts a wrong verdict | Score computed in code; second critic; disagreements shown |
| Keyword screener misses a brand or person | Responsible AI gap | "No people or hands" is on every checklist; limit stated in README |
| Network fails during the live demo | App can't generate | Phone hotspot; pre-generated results and screenshots |
| A member can't explain a part | Lost credit in the defense | Cross-review every PR; walk through all code together on Nov 1 |

## Week 9: the server

**Author:** Kuany Kuany
**Based on:** `intent/listing-agent.md`, `spec.md` ("Team Project 2: the MCP server")
**Approved by:** Kuany Kuany, 2026-11-26

### Files
| File | What it is |
|---|---|
| `server.py` | `MCPServer("listing")` with `find_images` and `request_generation`; `mcp.run()` over stdio. Imports `app.brief`, `app.screener`, `app.store`, `app.config` |
| `tests/test_find_images.py`, `tests/test_request_generation.py` | No-key tests through an in-memory `Client(mcp)`: no model, no network, no subprocess |
| `client.py` | A host with no model: starts `server.py`, lists the tools and schemas, calls each once |
| `.mcp.json` | Registers the server with Claude Code (`python3 server.py`) |
| `transcripts/week09-claude-code.txt` | One Claude Code session that used both tools (`/export`) |
| `CHECKS.md` | Week 9 section: tools table, `client.py` output, the stray-print error, Server or skill?, The gate |

### The first tools, and why these two
- `find_images` reads the system the task is about: the saved images and their briefs in `STORAGE_DIR`.
- `request_generation` is the tool that leads to spending money, so its gate goes first.

### Order
1. Working rules, intent, spec, dependencies (done in the first commit).
2. This plan, approved.
3. `tests/test_find_images.py`, failing → commit. `tests/test_request_generation.py`, failing → commit.
4. `server.py` with `find_images` → tests pass → commit. Then `request_generation` → commit.
5. `client.py`, its output and the stray-print error in `CHECKS.md`.
6. `.mcp.json`; each member runs it in Claude Code; one transcript committed.
7. `CHECKS.md` findings; tag `week09-submitted` on `main` after the PR is reviewed and merged.

### Who does what (proposed, team to confirm)
| Member | Does | Explains in the defense |
|---|---|---|
| Kuany Kuany | Plan, `find_images` tests and code, `client.py`, `.mcp.json` | everything, like every member |
| Jeevan Gowda Kumaraswamy | `request_generation` tests and code (it wraps his generation and store code) | |
| Abdel-Rhamane Sidally Toure | Reviews the PR, runs the server in Claude Code and saves the transcript, `CHECKS.md` findings | |

### Risks
| Risk | What we do |
|---|---|
| Something prints to stdout and breaks the protocol | `logging` to stderr only; we test the error once on purpose and record it in `CHECKS.md` |
| The model calls `request_generation` to "just make the images" | The tool never generates; it records a pending request, and the docstring says to tell the seller it is pending |
| A host bypasses our limits | The schema limits come from the same numbers as `ProductBrief`, and the function rebuilds a `ProductBrief`, so code checks again after the SDK |
| `/mcp` shows the server as failed | Start Claude Code from the repo root with `.venv` active; run `python3 server.py` by hand and read the error |
| Merge conflicts in `server.py` | One tool per person, pull before starting, commit small |
| The key leaks into a result | No Week 9 tool reads the key; `test_no_keys.py` still runs in the gate |

### Proof
| Tool | No-key tests (misuse cases) |
|---|---|
| `find_images` | listed with schema (`product` 1–80, `limit` 1–20, docstring says when to call); wrong type (`limit: "five"`) is an error result and the store is not read; out of range (`limit: 50`) is an error result; no match is `found: false` and not an error; the store unreadable (a file where the folder should be) is an error result with a message the model can act on |
| `request_generation` | listed with schema (brief limits, `variations` 1–5); wrong type (`variations: "two"`) is an error result and nothing is recorded; out of range (`variations: 9`, a 200-character name) is an error result; a brief that names a person is screened out as a normal result and nothing is recorded; the pending file cannot be written is an error result; **side effect:** after a valid call, no network connection was attempted, the generator was never called, no image was saved, and one pending request is on record |

**What registering in Claude Code proves that the tests do not:** that a host we did not write can start the server as a separate process over stdio, read its schemas and docstrings, and decide to call the tools from a plain-language request. It also shows how the host's own permission prompt behaves. The tests use the server object in memory, so they cannot catch a stray `print`, a wrong path or interpreter in `.mcp.json`, an import that only fails outside pytest, or a docstring that never makes a model call the tool.

### Questions asked, and how the plan changed
- **"A host sends this tool an argument of the wrong type. What comes back, and does our function run?"** The SDK validates the arguments against the schema built from the type hints, before our function. The host gets an error result (`is_error: true`), and the function body does not run. *Change:* the wrong-type tests also check that nothing was read or recorded, not just `is_error`.
- **"The server cannot ask the user anything. For the tool that changes something, what exactly happens when the model calls it, and who finishes the job?"** `request_generation` screens the brief, appends one pending line, and returns `generated: false, pending: true`. No image is made and nothing is spent. A person on the team reads `pending.jsonl` and approves it; the approval step runs the generator with the key from the environment, and it is not a tool. *Change:* the result carries `estimated_cost_usd`, so the person approving can see the cost, and the docstring tells the model to say "pending", not "done".
- **"Which of these tools could have been a script the agent runs from the shell, and what do we gain by putting it behind a server?"** `find_images` could be a script, or a skill that runs `ls generated/` and `jq`, for Claude Code alone. Behind the server, our own loop (a second host with no shell) gets the same tool. The UUID check and the store's format stay in one place, and the model cannot wander into other files. *Change:* none to the tools; the answer goes in `CHECKS.md` ("Server or skill?").
