# Product Listing Image Generator

Team Project 1, CPSC 415: Kuany Kuany, Jeevan Gowda Kumaraswamy, Abdel-Rhamane Sidally Toure.

A seller fills in a short product brief. The app generates listing images in five compositions (front, top-down, close-up, three-quarter, lifestyle) and sends each image itself to a vision model. The model answers a yes/no checklist made from the brief. Our code, not the model, then:
- checks every requirement was answered and none invented;
- computes the score;
- ranks the images;
- shows where a second vision model disagrees.

The chain: [intent/](intent/), [spec.md](spec.md), [plan.md](plan.md), [tests/](tests/), the pull requests with reviewer findings, [ANNOTATION.md](ANNOTATION.md), [CLAUDE.md](CLAUDE.md).

## Run it
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
cp .env.example .env        # put OPENROUTER_API_KEY=... in .env; never commit it
uvicorn app.main:app        # open http://127.0.0.1:8000
python -m pytest            # unit and browser tests; no key needed, nothing billed
```

## Models
| Job | Model (through OpenRouter) | Why |
|---|---|---|
| Generate | `black-forest-labs/flux.2-klein-4b` | About $0.014 per image, takes a seed, returns the bytes |
| Critique | `minimax/minimax-m3` | Class vision model; answers the checklist in JSON |
| Check the critic | `xiaomi/mimo-v2.6-flash` | A second company's model at a fraction of the cost; disagreements are shown |

The cheap vs. strong comparison is in [spec.md](spec.md), "Model comparison".

## Responsible AI
- **No people, no real brands.** Briefs that mention people or blocklisted brands (whole words, `app/screener.py`) are rejected before any billed call. Every prompt ends "Show only the product. No people, no hands, no text, no logos.", and every image's checklist includes "No people or hands appear in the image".
- **Provenance.** OpenRouter's Image API does not document C2PA for FLUX, and we check a saved file for a C2PA manifest (result under "Provenance check" below). Either way, every saved image gets our own metadata, written into the file (PNG `tEXt` chunks or a JPEG comment): `ai_generated=true`, model, seed, time, tool. Every image on the page is labeled "AI-generated mockup".
- **The critique can be wrong.** The page says so. The score is computed in code, and a second model's disagreements are shown.
- **Keys.** The only key is `OPENROUTER_API_KEY`, kept in the environment or a git-ignored `.env`. `tests/test_no_keys.py` scans every tracked file on every push and in CI.

## Provenance check
To be filled in from the first real image (Jeevan, `week06-jeevan`): whether the bytes FLUX returned contain a C2PA manifest, and the metadata our store wrote.

## Known limits
- **Screener:** a keyword list cannot catch every brand or every way of describing a person. It also rejects a few honest products whose name uses a people word on its own, for example "Model 3 charger".
- **Critic:** it can be confidently wrong. Two critics can be wrong the same way, so a person should look at the top pick.

## Cost
Running total from the OpenRouter Activity page (one key for the whole team). Under the ~$20 guideline.

| Date | What | Cost |
|---|---|---|
| 2026-10-31 | Development so far: all tests use fakes, no billed calls | $0.00 |
| | **Running total** | **$0.00** |
