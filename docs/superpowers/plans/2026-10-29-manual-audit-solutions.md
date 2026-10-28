# Manual audit and exercise solutions

The user authorizes verifying the board against the supplied manual, correcting
jumper accuracy, and adding solution code to the separate Lab exercises screen.
This supersedes the earlier removal of solution buttons; general help remains
absent. Root handles the manual audit and SVG; a parallel worker owns solutions.

- [x] Extract and inspect the supplied 61-page ALS board manual locally.
- [x] Record explicit two/three-pin jumper evidence and limits.
- [x] Correct SVG pin geometry, shunts, JP18 position and identifiable labels.
- [x] Add the manual-confirmed passive selectors for unmodeled interfaces.
- [x] Add a read-only numbered solution viewer, download and explicit IDE load.
- [x] Run build, all browser tests and backend tests; inspect and export SVG.

Manual evidence uses one-based PDF page numbers. JP4: page 25; JP5: page 26;
JP16: page 31; JP18 USB/ADC selection and location: pages 30, 34, 51;
JP7/JP8: pages 34, 50; JP12/JP13: page 35; JP17: page 50.
Only explicit positions containing pin 3 establish a three-pin selector;
short/open wording alone is not proof of physical pin count.

Preserve the current emulated subset, electrical mappings and manual wiring.
Static selectors for unmodeled interfaces are visual only, not fake simulation.
No new production dependencies. PDF extraction dependencies are local build tools.

## Continuation record

Ruling: resume implementation inline in the existing authorized workspace. There
is no Git repository, so Git worktrees, commits and branch integration do not
apply; progress remains in this plan. Existing solution code and tests are
preserved and verified rather than recreated.

Evidence: the 55 backend tests pass. The jumper browser test passed active
pin/shunt checks against a fresh service on port 8877, then failed on missing
passive JP7. The selectors are now added using the shared geometry component.
Ports 8765 and 8766 have older services; verification uses 8877 to avoid altering
an existing lab session. The production frontend is rebuilt in place.

Ruling: retain photo-backed two-pin geometry for JP5/JP16 and draw only the five
explicitly confirmed passive three-pin selectors. Short/open language alone
cannot prove a third pin; unsupported interfaces gain no simulated behavior.
Cost if the photo differs by board revision: approximate artwork may need a
further geometry correction, independently of the verified routing model.

Community research was attempted; the gateway returned an approval-policy
rejection. No external claims or citations were used. Impeccable's context
loader was unavailable without installing an engine outside the workspace;
the supplied manual, photos and incumbent implementation remain visual truth.

The full browser run passed 19/20. The physical JP5 click failed because its SVG
group's center fell in a blank gap between pins and silkscreen text. A transparent
hit rectangle now covers the jumper and label; keyboard focus also targets that
rectangle through the shared nested geometry. The original pointer regression
is retained for the next run.

Final review: a fresh read-only reviewer found one important upload race: an
already-submitted HEX request could replace a newly compiled solution even when
its stale response was ignored. The regression delaying the actual firmware
POST failed with compilation still enabled. Compile, HEX submission and source
replacement now share a synchronous firmware-operation guard; submitted HEX
uploads show Loading HEX and disable replacement until completion or failure.
Pending file reads remain cancellable, as verified by the existing test.

Final verification: production build passed; 55 backend tests passed; all 21
browser tests passed in 18.2 seconds on port 8877. No review findings remain
unaddressed. The reviewer set aside pixel alignment, mobile rendering and test
execution as outside the read-only inspection; root inspected desktop/mobile
captures, confirmed 430px document width and no browser errors, and checked
the actual command results. No minor findings were deferred.

Exported board/board.svg and build/vector-board-preview.png. The SVG parses as
XML with viewBox 0 0 1440 1040 and no images, scripts or external references.
Captures: build/manual-audit-{board,labs}-{desktop,mobile}.png.

Existing services on ports 8765/8766 were left untouched to preserve their
machines. Restart the launcher service to read the updated pinCount metadata;
the new production frontend otherwise sees the old cached API metadata.
