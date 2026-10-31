# Annotation

Four questions for each component: What is this? Why this choice? What breaks? What did I learn? Each owner writes their components' sections in their own pull request.

---

## Configuration and skeleton (`app/config.py`, `app/main.py`), Kuany

**What is this?** The FastAPI app and its settings. `config.py` reads the variation count, model names, storage folder and the API key from environment variables, or from a git-ignored `.env`. `main.py` holds the routes. The generator and critic are injected as FastAPI dependencies, so tests swap in fakes.

**Why this choice?** Settings are read on every call instead of cached, so a test can change `VARIATIONS` between two requests without restarting anything. Dependency injection is how the whole test suite runs with no key and no cost.

**What breaks?**
- A `VARIATIONS` value outside 1–5 raises an error, on purpose: there are only five compositions.
- If someone writes a model-calling route as `async def` with the synchronous SDK, every request waits behind it.
- FastAPI's own validation error is 422. We remap it to 400 so 422 can mean "screened out", as the spec says. A new route that relies on FastAPI's default would be inconsistent with the spec.
- **Found on Oct 31: loading `.env` on import broke the gate's promise.** The gate runs the tests with the key removed (`env -u OPENROUTER_API_KEY`), but `config.py` called `load_dotenv()` on import and put the key back. The billed `live` test then stopped being skipped. Now `tests/conftest.py` sets `APP_NO_DOTENV=1` before importing the app, and `test_the_test_session_never_loads_the_key_from_dotenv` keeps it that way.

**What did I learn?** A spec line like "FastAPI keeps serving while it waits" is only true for the way you write the route. It is a property of the code, not of the framework.

## Brief validation (`app/brief.py` and the form section of `app/static/app.js`), Kuany

**What is this?** The product brief: four required fields and two optional ones, each with a length limit. The page disables Generate until the brief is valid. The server checks the same rules again and returns 400 if they are broken.

**Why this choice?** The browser check is for the seller. The server check is for everyone else, because anyone can call the API without the page. Pydantic does the server check in a few lines.

**What breaks?** The limits live in two places, `brief.py` and `LIMITS` in `app.js`. If someone changes one, the two disagree. The tests catch the server side, and the browser test catches the page's required-field and length behavior.

**What did I learn?** "Required" needs a definition: a field of only spaces must count as empty. Both sides strip whitespace now, and there is a test for a field of spaces.

## Screening (`app/screener.py`, `app/blocklist.txt`), Kuany

**What is this?** It rejects a brief that mentions people (person, man, woman, hand, model, …) or a blocklisted celebrity or brand, before any billed call. It returns 422 with a fixed message.

**Why this choice?** A keyword list is free, instant, and testable. Asking a model would cost a call per click and could be wrong without telling us. The image model's own safety filter and the "No people or hands" checklist item are the backups.

**What breaks?**
- It misses people described in other words ("a shopper", "someone"), and brands that are not on the list.
- It rejects a few honest products that use a people word on its own ("Model 3 charger").
- Both limits are in the README.

**What did I learn? (the agent was confidently wrong)** The first spec, drafted by the agent, said to reject a brief if any field "mentions" hand, man or model. The agent presented this as finished. But matching substrings would have rejected the intent's own example, "Handwoven storage basket … leather handles", and things like "mango" or "manual". Sidally caught it in the PR #2 review. The screener now matches whole words, and the test `test_the_intents_own_example_passes` keeps it that way.

A second time: while writing the tests, the agent listed "Model 3 charger" as a brief that should pass. It does not pass, because "model" is a whole word there. The test run showed it, and the case became the documented known-limit test instead.

## Front end (`app/static/`), Kuany, with Jeevan's and Sidally's sections

**What is this?** One HTML page, one stylesheet, and plain JavaScript. `app.js` has a section per owner: Form, Grid, Critique. `ranking.js` sorts finished results.

**Why this choice?** One page with a form and a grid does not need React or a build step, and every one of us can read plain JavaScript.

**What breaks?** All three of us edit `app.js`, so merge conflicts are possible. The marked sections and the stacked branches keep the edits apart.

**What did I learn?** Playwright can fake our own API inside the browser (`page.route`). So the browser test checks the real page with no server-side model calls and no cost.

## Gate, guard and CI (`.git/hooks/pre-push`, `.claude/hooks/guard.py`, `.github/workflows/gate.yml`), Kuany

**What is this?**
- **Gate:** the pre-push hook runs `ruff` and the no-key tests before anything leaves the machine.
- **CI:** the same check runs on GitHub for every PR.
- **Guard:** it stops the agent from installing a package spec.md does not name, or from running destructive commands.

**Why this choice?** The gate is free and fast, so nobody is tempted to turn it off. It removes the key, so a test can never bill by accident.

**What breaks?**
- **Install false positive:** the guard reads the whole command text. While setting this repository up, it blocked an edit to `gate.yml` because the edit's text contained `pip install -r requirements.txt pytest ruff`.
- **Answer-key false positive:** its Week 5 "answer key" rule also blocks any shell command that mentions `images/` and writes a file, and our API route is `/api/images/{id}`. We kept the rule, because the lab image set in `images/` is evidence nobody should edit, and made those edits with the editor tool instead.
- **Inactive venv:** the gate runs whatever `python3` is active, so pushing without activating `.venv` fails the gate.

**What did I learn?** The guard checks whether a package name appears *anywhere* in spec.md, not under Dependencies. In my Week 5 repository, `pip install openrouter` was allowed before the spec named it as a dependency, because the spec mentioned "OpenRouter" in a sentence. A guard is only as precise as its matching rule.

## Prompts (`app/prompts.py`), Jeevan

**What is this?** It turns a brief into five prompts that are identical except for the composition: front, top-down, close-up, three-quarter, and lifestyle. Every prompt ends with "Show only the product. No people, no hands, no text, no logos."

**Why this choice?** Changing one thing and keeping the rest fixed gives the seller real options, and it makes the critique comparable across images. The checklist is the same for all five.

**What breaks?** The image model may ignore a line of the prompt, for example by putting a hand in the lifestyle scene or adding text. The prompt cannot enforce anything. The critique's "No people or hands" and "No text or logo" items are how we find out.

**What did I learn?** *(Jeevan: rewrite in your own words before merging.)* A prompt is a request, not a rule. The rule lives in the screener (before) and the checklist (after).

## Image generation (`app/generator.py`, `POST /api/generate`), Jeevan

**What is this?** One call to OpenRouter's Image API per image, with FLUX.2 klein. It uses a random seed and a 90-second timeout. The route builds the prompt, calls the generator, saves the result, and returns the image's id and URL. A failure returns 502 for that slot only, and no key returns 503.

**Why this choice?** FLUX.2 klein costs about $0.014 per image and takes a seed, which we save, so a person can regenerate the same picture. One request per image means one failure stays in one slot. The route is a plain `def` because the SDK client is synchronous.

**What breaks?**
- The key expiring or running out of credit: every slot shows "Image could not be generated", and we found this out on Oct 31 when our key had expired.
- Rate limits when five requests arrive at once.
- A timeout on a slow response.

The error message shown is short on purpose; the exception type is logged on the server, and the key never is.

**What did I learn?** *(Jeevan: rewrite in your own words before merging.)* The seed makes the picture repeatable, not the file: the Week 6 lab compares a same-seed rerun by eye and with `cmp`.

## Storage and provenance (`app/store.py`, `GET /api/images/{id}`), Jeevan

**What is this?** It saves each image as `<uuid>.<ext>` plus `<uuid>.json` (brief, variation, prompt, seed, model, cost, time, provenance).
- **With C2PA:** an image that arrives with a C2PA manifest, as every FLUX.2 klein image does, signed by Black Forest Labs, is saved **byte for byte**.
- **Without C2PA:** the image gets our own unsigned label, a PNG `tEXt` chunk or a JPEG comment.

The image route only accepts a lowercase UUID4, the only kind of id the server makes.

**Why this choice?**
- **Ids:** a client-supplied id that reaches the file system is how `../` attacks happen. Checking for a UUID4 before touching the disk closes that (PR #2 review).
- **Provenance:** a C2PA manifest carries a hash of the file's bytes, so adding even a comment segment would break the signature. Keeping the bytes is the only way to keep FLUX's real, signed provenance. Our label is the fallback for providers that don't sign.
- **No dependency:** detecting the manifest and writing the label both use the standard library.

**What breaks?**
- `has_c2pa_manifest` only looks for the JUMBF and `c2pa` markers. It does not validate the signature; `c2patool` would.
- Our fallback label is not signed, so anyone can strip or edit it.
- `generated/` grows forever: there is no cleanup.

**What did I learn? (the agent was confidently wrong, twice)** *(Jeevan: rewrite in your own words before merging.)*
- **First,** the agent wrote in spec revision 2 that FLUX "does not add C2PA", without checking, and built `store.py` to insert our own label into every JPEG.
- **Then** the reviewing agent flagged the spec change, and we checked the real files. Every FLUX image carries a C2PA manifest signed by Black Forest Labs, and Gemini's carries Google's. Our "provenance" code would have broken the real signature.
- **The fix:** a test that a C2PA image is saved byte for byte, then the code. Revision 1's simple rule, "save the exact bytes", had been right.
