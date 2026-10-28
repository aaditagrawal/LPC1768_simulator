# Separate Screens Implementation Plan

**Goal:** Provide dedicated Board, IDE and Lab exercises screens and remove
instructional help and solutions from the interface at the user's request.

**Architecture:** Hash navigation preserves the existing App-owned source,
firmware, selected exercise and physical state. Render one screen at a time.
The Board retains physical controls; the IDE retains code, uploads, downloads,
compile and diagnostics; Labs presents selectable exercise titles only.

**Scope:** Remove setup guides, connection checks, header pinout tooltips,
instruction banners, technical panels and reference-code buttons. Keep physical
labels, runtime controls, compiler/runtime errors and actual electrical warnings.
Keep the manual mapping and backend simulation unchanged. No dependencies.

**Review focus:** Source and compiled state survive navigation; manual hardware
is unchanged by exercise selection; held inputs release on leaving Board;
navigation supports deep links and browser Back; all screens fit narrow devices.

- [x] Add browser tests for separate screens, state retention and absence of help; observe failure.
- [x] Implement hash navigation, full-width screen layouts and task selection.
- [x] Remove help UI and tooltip answers while preserving hardware controls.
- [x] Update workflow tests; build and run browser verification on an isolated service.
- [x] Inspect screenshots, update documentation and obtain a read-only review.

## Results

The initial screen-separation test failed against the old shared workspace.
The final production build and all 12 browser tests pass against an isolated
service on port 8766. Desktop and mobile screenshots were inspected.

A regression test reproduced compiler errors being cleared by input release
on screen exit; build errors now have independent state. A read-only review
found that unmounting the IDE reset cursor and scroll. A failing browser test
confirmed it; a stable ref callback now stores and restores both. The final
suite checks line-number alignment after restoring a long source file.

No backend model or electrical mapping changed. The standalone SVG export was
regenerated without instructional tooltips. Community research was attempted;
the installed gateway requires account connection, so no external claims or
unverified citations were added.

Ruling: the user's request explicitly authorizes this layout and help removal;
routine implementation choices are settled here without a separate approval.
The filesystem workspace has no Git repository; changes remain in place.
