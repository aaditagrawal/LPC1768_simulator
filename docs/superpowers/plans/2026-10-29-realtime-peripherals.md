# Real-time peripheral timing implementation plan

**Goal:** real elapsed timer/PWM timing and a visible working seven-segment demo.
**Spec:** ../specs/2026-10-29-realtime-peripherals-design.md
**Architecture:** monotonic live peripheral clock; deterministic offline clock;
bounded firmware worker; unchanged HTTP presentation cadence.
**Tech stack:** existing Python, Unicorn, Keil, pytest, Playwright.

- [x] Add failing compiled-firmware clock tests for PCLK divisors, fractional
   prescaler state, timer reset/stop/match flags, PWM, pause/resume and clock
   changes. Back up touched source files because this directory has no Git repo.
- [x] Implement clock derivation and elapsed-time timer advancement in engine.py,
   reusing the existing match/IRQ logic. Preserve deterministic offline behavior.
- [x] Switch live Runtime machines to real time, freeze/reanchor on control changes,
   and replace unconditional 2 ms worker sleeping with bounded CPU execution.
- [x] Give live seven-segment decoding a time-based persistence window. Validate
   with the user's corrected program and measured count transitions.
- [x] Run regression suites, review changes, update timing documentation and API
   metadata, restart the local service with the corrected demo, and verify its
   visible behavior. Preserve source/wiring where possible and leave web polling
   unchanged.

Review focus: register changes must not reinterpret old elapsed time at a new
frequency; pauses must not accumulate; host stalls must not create unbounded
match loops; millisecond polling must not lose most timer periods; display
history must age with simulated active time. CPU delay loops remain an explicit
limitation rather than being replaced with source-aware animations.

Completed: 117 backend checks, 27 browser checks and the frontend build pass.
Review caught unreachable-stop batching and PR/PC equality handling; both were
fixed and rechecked. Display reconstruction retains instruction dwell weighting
while expiring by active time, preserving fast software multiplexing. Main service
was restarted and the corrected counter demo loaded with its three manual cables.
