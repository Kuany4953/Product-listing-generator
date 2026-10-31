# Project conventions

## What this repository is
Team Project 1: a FastAPI web app that generates product listing images from a seller's brief and critiques each one with a vision model. Plain code then checks the critique: the score is computed from the checklist, and a second model's disagreements are shown. The design is in [spec.md](spec.md), the build order and owners in [plan.md](plan.md), and the features in [intent/](intent/).

## Commands
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && python -m playwright install chromium   # once
cp .env.example .env            # then put your key in .env (never commit it)
uvicorn app.main:app --reload   # run: http://127.0.0.1:8000
python -m pytest                # test: unit + browser, no key needed, nothing billed
set -a; . ./.env; set +a; python -m pytest -m live   # the billed live test: the key must be exported
                                # (tests never read .env themselves: APP_NO_DOTENV=1 in tests/conftest.py)
ruff check .                    # lint
cp path/to/ai-integration-course/examples/pr-review/gate.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
python3 path/to/ai-integration-course/examples/pr-review/review.py > review.txt   # reviewer, from repo root
```
Activate `.venv` before `git push`. The pre-push gate runs `python3 -m pytest` and `ruff`, which must be the venv's.

## Conventions
- Python 3.12+, FastAPI, plain HTML/CSS/JS. No framework on the front end, no build step.
- **Back end layout:** one module per component in `app/` (see spec.md, "Project layout").
- **Front end layout:** `app/static/app.js` has one marked section per owner (Form, Grid, Critique); ranking lives in `app/static/ranking.js`.
- **Tests:** in `tests/`, named `test_<module>.py`, plus browser tests in `tests/browser/`. They use the fakes in `tests/conftest.py` (`FakeGenerator`, `FakeCritic`) through `app.dependency_overrides`.
- **Billed tests:** a test that calls a real model is marked `live` and skipped without a key.
- **Branches:** `week06-<name>`, one PR each, reviewed by a different member after the reviewing agent's findings are posted on the PR.

## Working rules
- Write or update `intent/` and `spec.md` before code. `plan.md` says who builds what, in which order.
- One feature per branch and pull request. Never push to `main` directly. Tests first: the red commit comes before the code commit.
- **Keys:** never commit `.env` or `.claude/settings.local.json`. The only key is `OPENROUTER_API_KEY`, from the environment. `tests/test_no_keys.py` scans every tracked file.
- **Dependencies:** name each one in spec.md under Dependencies, with the reason, before installing it. The guard hook blocks installs that spec.md does not list.
- **Cost:** image generation and vision calls are billed. Use `VARIATIONS=1` in development. Never call a model inside a non-`live` test or in a loop.
- **The critic:** its output is model output. The code computes the score from the checked checklist. Never take a score, verdict or ranking from the critic's text.
- **Responsible AI:** no people or real brands. A screening change must keep the whole-word rule and its tests. Every saved image gets provenance metadata and the "AI-generated mockup" label.
- **Image ids:** ids are UUIDs made by the server. Any route that reads a file checks the id first.

## Common mistakes
Things the agent got wrong before and must not repeat.
- **Screening by substring.** It rejected "Handwoven … leather handles", the intent's own example. Match whole words.
- **`git commit -am` with unrelated edits in the tree.** It swept an unrelated README edit into a spec commit. Stage files by name.
- **Commands that mention a package install inside a string.** The guard reads them as an install, for example editing a YAML line that contains `pip install`. Use the Edit tool for such edits.
- **Calling the sync OpenRouter client inside an `async def` route.** It blocks the server. Model-calling routes are plain `def`.
