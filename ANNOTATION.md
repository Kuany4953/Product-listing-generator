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

**What is this?** It saves each image as `<uuid>.<ext>` plus `<uuid>.json` (brief, variation, prompt, seed, model, cost, time). Before saving, it writes provenance into the image itself:
- PNG: `tEXt` chunks.
- JPEG: a comment segment.

The image route only accepts a lowercase UUID4, the only kind of id the server makes.

**Why this choice?**
- **Ids:** a client-supplied id that reaches the file system is how `../` attacks happen. Checking for a UUID4 before touching the disk closes that (PR #2 review).
- **Provenance:** OpenRouter does not document C2PA for FLUX, so we add our own metadata where the format allows it, without changing a pixel.
- **No dependency:** both formats are simple enough to write with the standard library.

**What breaks?**
- A format we don't handle (WebP) is saved without embedded provenance; the JSON sidecar still has it.
- Our metadata is not signed, so anyone can strip or edit it. Real C2PA is signed; ours is a label, not proof.
- `generated/` grows forever: there is no cleanup.

**What did I learn?** *(Jeevan: rewrite in your own words before merging.)* "Provenance where the API supports it" needs checking, not assuming. Revision 1 of the spec assumed the image API would add C2PA; with FLUX we had to add a label ourselves and say how weak it is.

## Vision critique (`app/critic.py`, `POST /api/critique`), Abdel-Rhamane

**What is this?** For each image, the back end loads the **saved file** by its id and sends it to `minimax/minimax-m3` with a yes/no checklist built from the brief: product, color, material, background, style, no people, no text. The image goes as a base64 data URL in an image content part. A second model, `xiaomi/mimo-v2.6-flash`, answers the same checklist. Each model gets two tries for a usable reply. Otherwise the result is "Critique unavailable".

**Why this choice?**
- The assignment requires that the critique reads the image, not the prompt. The test `test_the_critic_receives_the_saved_image_not_just_the_prompt` checks that the bytes sent are the bytes saved.
- A checklist the model must answer item by item is checkable in code. An open-ended "what's wrong with it?" is not.
- The second model is cheap, and in the Week 6 lab a single critic was confidently wrong about text the generator got right.

**What breaks?**
- The critic can be wrong, and two critics can be wrong the same way. Disagreements are shown, but agreement is not proof.
- mimo returns an empty reply if hidden reasoning is on, so it is turned off per model in `REASONING`.
- An API error or timeout makes that image "Critique unavailable". It is never a crash.

**What did I learn?** *(Abdel-Rhamane: rewrite in your own words before merging.)* "The critique reads the image" is a claim you can test: a fake client captures the request, and the test looks for the image part.

## Checking the critique and the score (`app/critique_parser.py`), Abdel-Rhamane

**What is this?** Plain code, no model. It:
- extracts the JSON from the reply, even inside a code fence or prose;
- matches the critic's answers to our checklist, ignoring case and punctuation;
- reports requirements the critic **did not answer**, items it **invented**, and items it said were not met;
- computes the score: the share of requirements met, out of 10, minus 1 per listed problem (at most 3).

**Why this choice?** Revision 1 of the spec had the model write the score. A model's number is model output: it can contradict its own checklist ("color: does not match" with "score: 9"). Computing it in code makes the score follow from the checks, and the test `test_the_models_own_score_is_ignored` keeps it that way.

**What breaks?**
- If the critic copies a requirement with different wording ("The item is navy"), it counts as missing plus invented. That is strict, but visible.
- The score weighs every requirement equally, so "no text" counts as much as "right color".

**What did I learn?** *(Abdel-Rhamane: rewrite in your own words before merging.)* The parser's job is not to make the critic's reply valid but to say exactly what is wrong with it. An unanswered requirement is a problem even when every answered one passes.

## Ranking and the critique panel (`app/static/ranking.js`, critique section of `app.js`), Abdel-Rhamane

**What is this?** Under each image: the score, the checklist with the critic's evidence, problems, anything the critic missed or invented, and "Critics disagree on: …" when the two models differ. When every slot is finished, `rankSlots` sorts by score. Critique unavailable and failed generation go last, and ties keep the variation order. The first gets "Top pick". The panel says "AI critique: checks the image against your brief only and may be wrong."

**Why this choice?** In revision 1, a failed generation never got a critique, so ranking waited forever. That was point 3 of the PR #2 review. Counting "failed" as finished fixes it, and the browser test `test_failed_generation_counts_as_finished_and_goes_last` proves it.

**What breaks?** After a Retry, the slot is pending again, and the ranking redraws when it finishes. If the seller clicks Generate again mid-critique, late replies from the old run update detached elements and are ignored.

**What did I learn?** *(Abdel-Rhamane: rewrite in your own words before merging.)* JavaScript's sort is stable, so "ties keep their order" needs no extra code, but it does need a test.
