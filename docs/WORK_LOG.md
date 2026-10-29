# Implementation and review record

## 2026-10-29 hardware-fidelity audit

Read both board/lab PDFs, established the documented wiring/register scope,
and added independent finite-state, compiled-firmware, timing and mutation
checks. Corrected 24 grouped model defects and seven reference-firmware issues.
The final consolidated run passed 557 backend cases, 29 browser cases and the
frontend build. Separate ledgers contain 33,123 passing input observations;
28/28 named mutations are detected. Replaying 41 regressions against the original
Git snapshot produces 41 expected failures with raw traces.

The root TEST_REPORT.md, HARDWARE_SPEC.md, COVERAGE_MATRIX.md and
HARDWARE_FIDELITY_GAPS.md are the current audit records. Earlier entries below
are historical. Physical fidelity remains unverified, and accepted storage
for an unimplemented register is not evidence of hardware support.


* Repository initially held only manuals and JPEGs; no source or git repository.
* User's detailed implementation specification authorized the backend spike and
  smallest viable end-to-end app. No extra design/approval gate was introduced.
* Keil inspection found µVision 4.70a / ARM5.03 Lite and usable local CMSIS.
* Backend gate passed before UI: real Keil HEX emitted GPIO SET/CLR in Unicorn.
* Fixed wiring graph and event decoders implemented with firmware integration
  tests first. Failed tests exposed weak-pull LED routing and invalid API types.
* Eighteen corrected standalone lab programs added, preserving original PDFs.
* Local worker/API and photo-overlay interface implemented and exercised in
  Chromium against the actual service.
* Independent review found four important defects. Each received a failing
  regression before its fix: held level/uncleared IRQ requests, timer events
  across MR0 reset/stop, reference-source races during builds, and queued press
  events arriving after window-blur release. Corrected and retested.
* Initial browser cable test clicked the empty middle of the curved path's
  bounding rectangle. It now clicks an actual point on the cable stroke.
* Public community research through DevRelay was attempted but returned a login
  requirement. No account was connected: the requested local project requires
  no cloud authentication. No community claims or invented citations were used.

Decisions: use installed Keil compiler with Unicorn rather than spending more
time on an unverified proprietary simulator bridge; default SW2 to the lab's
pin 7 with an explicit conflicting profile; omit unverifiable POT5; approximate
timer rates while preserving match/interrupt logic; use the supplied clearer
JPEG and editable approximate overlay coordinates. Costs/limits are recorded
in ARCHITECTURE.md, BOARD_NOTES.md and LAB_COVERAGE.md.

Final verification on 2026-10-29: `python -m pytest -q` completed with **54
passed**; `npm run test:browser` completed with **6 passed** against the real
local service; `npm run build` passed TypeScript and Vite production compilation.
Environment: Python 3.14.3, Node 24.14.1, Unicorn 2.1.4, installed Keil ARM5.03.
Launcher start/stop was exercised and the service was left at a clean empty
machine with no attached cables and open jumpers. Browser screenshots are in
`test-results/board-desktop.png`, `lcd-firmware.png` and `board-mobile.png`.

## Manual audit and solution viewer continuation — 2026-10-29

Completed the pending manual-audit-solutions plan. Physical jumper pin counts
and shunt placement are explicit; JP18 sits in the USB device section. Added
the manual-confirmed passive JP7/JP8, JP12/JP13 and JP17 selectors, corrected
identifiable labels, and documented the distinction between manual evidence,
photo-backed geometry and approximate positions. Passive parts do not extend
emulation. Removed the stray trailing backtick from start.bat.

Verified the read-only numbered solution viewer, exact C downloads and explicit
IDE replacement. Browsing preserves source, firmware and hardware. A failing
browser test exposed an SVG click gap around JP5; a shared hit rectangle now
provides pointer coverage and visible keyboard focus. Fresh read-only review
found an already-submitted HEX upload could overwrite a newer compilation.
A regression reproduced the missing operation guard, then passed after HEX
submission and compilation shared the same synchronous guard. Pending file
reads still cancel when opening a solution.

Final evidence: 55 backend tests passed, all 21 browser tests passed (18.2s),
and TypeScript/Vite production build passed. Desktop/mobile captures were
inspected with no page errors or horizontal document overflow. Regenerated
board/board.svg and build/vector-board-preview.png; SVG XML validation found
no images, scripts or external references. Community lookup was rejected by
the tool approval policy; no external claims were used. Existing lab services
were preserved; restart the launcher to pick up updated board metadata.

## Jumper visibility and interaction repair — 2026-10-29

The user's running service still returned jumper metadata without pinCount.
The rebuilt frontend treated it as mandatory, producing NaN SVG geometry and
invisible/non-clickable active headers including JP5. A browser regression
that removed pinCount reproduced the missing pins. Board geometry now falls
back to the bundled canonical mapping, so refreshing the frontend fixes the
existing session without a backend restart.

The user also requested interactive shunts for the added selectors. JP7, JP8,
JP12, JP13 and JP17 now accept pointer and Enter/Space input; positions persist
in browser storage across navigation and reload. These interface models remain
unsupported and selector movement does not change firmware routing. A missing
controls regression failed first and then passed after implementation.

Fresh read-only review found JP16's transparent hit rectangle overlapped the
physical center of JP17. Clicking JP17's actual middle pin reproduced the
interception. JP16's label now sits above the header and its hit area stops
before JP17's body. The regression clicks each added selector's middle pin,
then uses the keyboard and verifies persisted state and unchanged routing.

Final evidence: production build passed; all 23 browser tests passed (20.4s),
and 55 backend tests passed (45.66s). Desktop/mobile inspection against the
actual older service at 8765 confirmed valid geometry for all four active
jumpers, visible JP5, no console/page errors, and a 430px mobile document width.
Existing firmware was not stopped or restarted. Screenshots are
build/jumpers-fixed-desktop.png and build/jumpers-fixed-mobile.png; standalone
board SVG and preview were regenerated against the isolated verification
service. The review's only important finding was fixed; none were deferred.
Community lookup required an MLH account, so no external claims were used.
