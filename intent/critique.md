# Intent: Critique Images Against the Brief

**Status:** Draft (pending review)
**Author:** Kuany Kuany
**Approved by:** Jeeve Gowda

## Problem
Image models often get details wrong: wrong color, extra objects,
wrong background. A seller choosing between 5 images needs to know
which ones actually match their product and what is wrong with the
rest, without checking every detail by eye.

## Who uses it
The same seller, right after their images are generated.

## User flow
1. As each image finishes generating, it is sent for critique.
2. A score and checklist appear under each image.
3. When all 5 are critiqued, the images are ranked by score and
   the best one is highlighted as "Top pick."

## Behavior
- The back end sends the generated image itself (the actual image
  data, not only the prompt) plus the original brief to a vision model.
- The vision model checks each brief item and returns structured
  output, for example:
  - Color: matches / does not match, with a short reason
  - Material: matches / does not match
  - Background: matches / does not match
  - Style: matches / does not match (if given)
  - Problems: anything else wrong, such as extra objects or
    distorted shapes
  - Score: 0 to 10
- The response must be in a fixed format (e.g., JSON) so the app
  can display it and rank the images reliably. If the model returns
  something unreadable, the app retries once, then shows
  "Critique unavailable" for that image.
- Ties in score keep the original generation order.

## Proof the critique reads the image
The critique must mention details that are only visible in the
image, not in the brief. Example: if the brief says "white
background" and the image has a gray one, the critique must say
the background is gray.

## Responsible AI
- The critique judges the image against the brief only. It does
  not make claims about the real product's quality or safety.
- The UI makes clear the critique is AI-generated and can be wrong.

## Out of scope
- Automatically regenerating bad images.
- Predicting sales or buyer interest.

## Acceptance criteria (these become tests)
- [ ] Each displayed image gets a score and checklist.
- [ ] An image with a deliberately wrong color (test image) is
      marked "does not match" for color.
- [ ] Images are sorted by score, and the highest is labeled
      "Top pick."
- [ ] A malformed model response shows "Critique unavailable"
      without crashing the page.
- [ ] The request to the vision model contains image data
      (checked in a unit test with a mocked API).

## Open questions
- Which vision model? A cheap and a strong model will be compared
  on real generated images. (Decided in spec.md.)
