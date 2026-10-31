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

**What breaks?** The guard reads the whole command text. While setting this repository up, it blocked an edit to `gate.yml` because the edit's text contained `pip install -r requirements.txt pytest ruff`: a false positive. The hook only checks the active venv's tools, so pushing without activating `.venv` fails the gate.

**What did I learn?** The guard checks whether a package name appears *anywhere* in spec.md, not under Dependencies. In my Week 5 repository, `pip install openrouter` was allowed before the spec named it as a dependency, because the spec mentioned "OpenRouter" in a sentence. A guard is only as precise as its matching rule.
