# Intent: Generate Product Listing Images

**Status:** Draft (pending review)
**Author:** Kuany Kuany
**Approved by:** [teammate name], [date]

## Problem
Small sellers on online marketplaces often lack professional product
photos. Good listing images strongly affect whether buyers click and
purchase, but photo shoots cost time and money. Sellers need a fast
way to see what a strong listing image of their product could look like.

## Who uses it
A seller preparing a product listing. They know their product well
but are not photographers or designers.

## User flow
1. The seller opens the app and sees a product brief form.
2. They fill in the brief and click "Generate."
3. The app shows a loading state while images are created.
4. Five image variations appear in a grid as they finish.
5. Each image is then sent to the critique feature (see critique.md).

## Inputs: the product brief
| Field | Required | Example |
|---|---|---|
| Product name | Yes | Handwoven storage basket |
| Color | Yes | Navy blue |
| Material | Yes | Seagrass |
| Background | Yes | Plain white / wooden table / outdoor |
| Style | No | Minimal, natural light |
| Extra details | No | Has leather handles |

- Required fields must be filled before Generate is enabled.
- Each field has a length limit (TBD) to control prompt size and cost.

## Behavior
- The back end builds one prompt from the brief. Each of the 5
  variations uses the same brief with a different camera angle or
  composition (e.g., front view, top-down, close-up, angled, lifestyle
  scene without people), so the seller gets real options.
- The number of variations is a configuration setting, default 5.
  During development the team uses 1 to save cost.
- If one variation fails, the others still display, and the failed
  slot shows an error message with a retry button.
- Generated images are saved with their brief, so the critique and
  any later comparison use exactly the same image the seller saw.

## Responsible AI
- No images of real people. Prompts instruct the model to show the
  product only. Briefs that ask for people, celebrities, or real
  brand logos are rejected with a clear message.
- Generated images keep provenance metadata where the image API
  supports it. The UI labels every image "AI-generated mockup."
- API keys come from environment variables only and are never
  committed. `.env` is listed in `.gitignore`.

## Out of scope
- Editing or retouching images.
- Uploading the seller's own product photo (possible stretch goal).
- Posting images to a real marketplace or ad platform.

## Acceptance criteria (these become tests)
- [ ] Submitting a valid brief displays 5 images.
- [ ] Submitting with a required field empty is blocked in the UI.
- [ ] A brief mentioning a person or a real brand is rejected.
- [ ] If one generation fails, the remaining images still display.
- [ ] Changing the variation setting to 1 produces exactly 1 image.
- [ ] No API key appears in any committed file.

## Open questions
- Which image model? (Decided in spec.md.)
- Generate all 5 at once (faster) or one at a time (simpler)?
