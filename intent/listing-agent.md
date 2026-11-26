# Intent: Listing Agent (Team Project 2)

**Status:** Draft
**Author:** Kuany Kuany
**Approved by:** _(name, date)_

## Problem
In Team Project 1 a seller fills in a form and the page generates and critiques images. A seller who works with a coding agent or a chat assistant cannot use that page from there. Every generated image also costs money, even when a suitable image for the same product already exists.

## What it does
An MCP server exposes the listing generator as tools, so any MCP host (Claude Code, and our own agent loop) can:

1. find listing images that were already generated for a product, and reuse them instead of paying for more;
2. ask for new images from a brief. The request is screened by the same whole-word rule as TP1 and recorded as **pending**. A person on the team approves it before anything is generated or spent.

Later tools (critique a saved image, report the ranked set) come after Week 9. They are listed in spec.md.

## Who uses it
A seller, through an agent. The agent plans, calls the tools, reads the results, and tells the seller what was found or what is waiting for approval.

## What the agent may and may not touch
- **May:** read the saved images and their briefs in `STORAGE_DIR`, and append a pending request to `pending.jsonl`.
- **May not:** generate an image, call any model, spend money, delete or change a saved image, or read any file outside `STORAGE_DIR`. Generation happens only after a person approves the pending request.
- **Never** returns the API key or any setting that holds it.

## Acceptance criteria
- A host lists the tools and receives each one's schema, with the brief limits from spec.md ("Product brief rules").
- Searching for a product with no saved images returns "nothing found" as a normal answer, not an error.
- A request for images of a person or a real brand is refused by the screener, and nothing is recorded.
- A valid request is recorded as pending; no image is generated, no model is called, and nothing leaves the machine.
- Bad arguments (wrong type, too long, too many variations) are refused before our code runs.
- If the image store or the pending file cannot be read or written, the agent gets an error it can report, not a crash.

## Out of scope
Same as TP1: no people or real brands, no editing images, no posting to marketplaces. No tool completes a billed action on a model's request.
