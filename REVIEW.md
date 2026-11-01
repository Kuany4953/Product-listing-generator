# Review policy

<!-- A separate reviewing agent reads this when reviewing a pull request.
     Passes are ranked by severity. A pull request fails review on any finding in pass 1 or 2. -->

## Pass 1: Must not merge
- Secrets, keys, or tokens in the diff or in history.
- Code that does not match `spec.md`, or a spec that was silently changed to match the code.
- Tests that were deleted, skipped, or weakened to make the build pass.
- Destructive operations without a guard (file deletion, payments, external writes).
- A route that reads a file from a client-supplied id without checking it is a UUID (path traversal).
- A billed model call inside a test that is not marked `live`, or inside a loop with no bound.
- A prompt or screening change that would let a brief ask for real people, celebrities, or brands.

## Pass 2: Must fix before merge
- Model output used as fact without validation (structured output not checked, no refusal handling).
- Missing error handling for the failure cases listed in `spec.md`.
- No test for the behavior the PR claims to add.
- A score, verdict, or ranking taken from the critic's text instead of computed in code from the checked checklist.
- Generated images saved without the provenance metadata spec.md requires, or without the "AI-generated mockup" label in the UI.

## Pass 3: Should fix
- Duplicated logic, dead code, unclear names.
- Cost: unnecessary calls, oversized prompts, a frontier model where the spec chose a cheap one.

## Pass 4: Nice to have
- Documentation and comment quality.

## How to report
One finding per line: severity, file and line, what is wrong, what to do instead.
