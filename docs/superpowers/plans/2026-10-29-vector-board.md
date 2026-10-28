# Vector Board Implementation Plan

**Goal:** Replace the board photograph with a complete interactive SVG replica.

**Architecture:** A BoardArtwork component draws static PCB geometry and
component bodies; Board renders stateful components and wiring over it.
Layout JSON supplies shared positions and connector orientations.

**Tech Stack:** Existing React, TypeScript, native SVG and Playwright.

**Spec:** ../specs/2026-10-29-vector-board-design.md

## Constraints

- Preserve board/mapping.json and firmware simulation behavior.
- Use the supplied uncabled photograph as the visual reference.
- No raster images, external graphics or added dependencies.
- This directory has no Git repository; edit the authorized workspace in place.

## Review focus

- Rotated connector geometry must agree with cable endpoints and pointer targets.
- Decorative components must not intercept controls or claim emulation.
- Firmware display changes must remain visible over the vector component bodies.
- Keyboard and pointer release must retain their existing behavior.
- Zoom must stay within the board scroller on narrow screens.

## Tasks

- [x] Add and run a browser regression asserting a complete vector board with no raster image.
- [x] Draw reusable PCB parts and the physical board sections in web/BoardArtwork.tsx.
- [x] Update layout.json, Layout types and Board.tsx controls to align with the artwork.
- [x] Build, run the browser suite against an isolated local service, inspect screenshots.
- [x] Export a standalone SVG snapshot, document fidelity limits and review the result.

## Verification

The new browser test initially failed because the photo was still present.
After implementation, the production build and all 7 browser tests pass against
an isolated local service on port 8766. All 54 backend tests pass. The SVG
export parses as XML with a 1440 × 1040 viewBox and no image, script or external
asset references. A read-only reviewer checked the code and reference photo;
minor label overlaps were corrected and the final preview inspected again.

Ruling: the request specifies a complete SVG replacement and supplies the board
reference, so routine drawing choices were made within that authorized scope.
No Git operations were attempted because this workspace has no repository.
Community research was attempted but the installed gateway requires an account
connection; no external claims or unverified citations were used.
