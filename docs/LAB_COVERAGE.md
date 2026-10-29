# Lab coverage

Historical pre-audit record: current results, corrected reference behavior and
coverage are in [TEST_REPORT.md](../TEST_REPORT.md),
[HARDWARE_SPEC.md](../HARDWARE_SPEC.md) and
[COVERAGE_MATRIX.md](../COVERAGE_MATRIX.md). The earlier results below are
retained for provenance and do not describe the current model.

See the [29 October 2026 peripheral connectivity audit](PERIPHERAL_CONNECTIVITY_AUDIT.md)
for manual-derived routing checks, exact connections/jumper requirements,
unsupported interfaces and reference timer/interrupt differences.

Working = supported by the implemented register/board subset and a runnable
corrected reference. Verification below distinguishes behavioral assertions
from compile/boot checks; compile/boot alone is not proof of every counter
sequence or arbitrary student program.

| Exercise | Status | Verification |
|---|---|---|
| Lab 6 LED blink | Working | Real firmware observed both all-on and all-off |
| Lab 6 switch on P2.12 | Working | Press/release changes firmware-driven LED |
| Lab 7 serial ON/OFF | Working | Reference boots; successive 1,3,7 outputs asserted; GPIO SET/CLR and cable removal separately tested |
| Lab 7 binary up | Working | Reference advances through binary 1 and 2 |
| Lab 7 SW2 up/down | Working; partially verified | Reference compiles/boots; shared SW2 polling path tested; complete up/down sequence not separately asserted |
| Lab 7 ring | Working | Three SW2 edges advance 1→2→4→8; held switch does not repeat |
| Lab 8 BCD up | Working; partially verified | Reference compiles/boots; four-digit GPIO multiplex decoder tested against known segment patterns; counter rollover not separately asserted |
| Lab 8 timer + BCD up/down | Working; partially verified | Reference compiles/boots; Timer0 match/IRQ and alternate SW2 route available; rollover/direction sequence not separately asserted |
| Lab 8 binary ring | Working; partially verified | Reference compiles/boots; shared multiplex decoder tested; complete ring cycle not separately asserted |
| Lab 8 BCD down | Working; partially verified | Reference compiles/boots; shared multiplex decoder tested; rollover not separately asserted |
| Lab 8 hexadecimal up/down | Working; partially verified | Reference compiles/boots; shared timer/decoder paths tested; all 16 glyphs/direction changes not separately asserted |
| Lab 9 message | Working | Exact two-line text asserted from actual GPIO edge decoding, also through browser HEX upload |
| Lab 9 dice | Working | SW2 displays 1–6; holding does not roll again |
| Lab 9 keypad keycode | Working | All 16 browser keypad controls reach LCD; firmware probes cover every row/column through all four MCU headers and JP4 gating |
| Lab 9 calculator | Working | Actual key presses produce `3+4=7` and `2-8=-6` |
| Lab 10 ADC0.5 | Working | POT1 endpoint readings produce `4095 3.300V` and `0 0.000V` on LCD |
| Lab 10 ADC4−ADC5 | Working | Signed count-difference reference; 4095 versus 0 and JP18 disconnect asserted |
| Lab 11 basic PWM | Working | Static 25% duty, cable gating and MR4 changes from actual PWM interrupt handler asserted |

All 18 references are separately compiled and booted. Tests do not match source
filenames or substitute predetermined peripheral outputs.

## Additional regression coverage

* Real Keil HEX executes installed startup, CMSIS SystemInit and runtime init.
* LEDs cease receiving output when a cable is disconnected; raw GPIO latch remains.
* Incorrect MCU-header wiring does not create the expected LED signals.
* One cable per header; conflicting driven nets produce warnings.
* GPIO masks, byte access and PINSEL affect signal availability.
* Manual-derived probes cover each LED line through CNA/CNB/CNC/CND, SW2
  through every header, all segment bits on every digit, hex glyph patterns,
  ADC voltage/mux/power/jumper gates, six PWM duty settings, EINT2-driven LD10
  and Timer0–Timer3 match handlers.
* The Lab 11 keypad/PWM exercise is verified with separate CNB→CNB1 and
  CNC→CNB3 cables and corresponding GPIO firmware. It has no built-in reference.
* LCD data is decoded at enable falling edges; JP5 and JP16 gate it.
* Seven-segment state is reconstructed from every data/address change and dwell,
  so inter-digit blanking is distinguished from the displayed pattern.
* SW2 invokes an actual EINT2 handler and returns to the interrupted program.
* Held/uncleared peripheral interrupt requests re-pend; Timer0 MR1 before an MR0
  reset is retained, and stop-on-match holds the match count.
* Bad HEX, invalid physical inputs, failed compilation and unknown MMIO have
  explicit errors; failed builds/uploads preserve the previous machine.
* Pause/resume/stop/reset, source/compile races, and queued input release on
  window blur are tested. Reset preserves physical setup.
* Browser tests exercise C compilation, HEX upload, manual cable click removal,
  jumper changes, momentary keyboard controls and a narrow viewport against
  the real local backend. Board, IDE and Lab exercises use separate screens;
  tests cover source retention, browser Back, direct links, compilation during
  navigation, persistent compiler errors and release of held inputs on exit.
* The learning interface exposes task titles and read-only, numbered C solutions,
  with download and explicit Open in IDE actions. Selecting or viewing a task
  leaves source, firmware and physical setup unchanged; opening its solution
  replaces source and requires compilation. Wiring help, connection checks,
  pinout tooltips and technical panels remain absent.
* Solution browser tests cover exact downloads, explicit replacement, source
  and physical-state preservation, stale responses, retry, compilation races
  and cancellable file reads. A submitted HEX upload blocks compilation and
  replacement until it settles, preventing older firmware from overwriting
  a newly compiled solution.
* Jumper browser coverage checks physical pin counts and that a shunt covers
  exactly pins 1–2 or 2–3. Manual-confirmed selectors for unsupported interfaces
  have movable, browser-persisted shunts without electrical effects; JP18 is
  drawn in the USB device section. Regression coverage includes missing pinCount
  metadata from an older service, active jumper pointer/keyboard operation,
  and extra selector positions surviving navigation and reloads.
* The complete board is native SVG, including the PCB and component bodies;
  browser coverage checks that no raster board image is used, that the physical
  sections and all supported headers remain visible, and that zoom stays within
  the board scroller on a narrow viewport. This does not add peripheral models.

## Unsupported and blocked items

Live timer/PWM elapsed-time operation now uses a monotonic clock and configured
clock divisors; pause/resume excludes paused time. See [TIMING](TIMING.md).

| Item | Status / reason |
|---|---|
| Keil simulator as a live external execution backend | Unverified integration; documented automation exists, but a lossless GPIO bridge/AGSI integration was not established. Installed Keil compiler is used successfully. |
| Definitive physical SW2 trace | Blocked by contradictory manuals; lab pin-7 profile and explicit alternative provided. A schematic/continuity measurement could settle it. |
| POT5 ADC route | Unsupported: route not established; POT1 is not substituted. |
| Nested NVIC/priority preemption, SysTick, RTOS/PSP, bit-band, IAP | Unsupported; outside the implemented minimal CPU-peripheral integration. |
| Exact CPU cycles / high-frequency waveforms | Unsupported: CPU/IRQ throughput is host-limited. Elapsed timer/PWM counters and clock divisors are modeled, but oscilloscope-level edge timing is not certified. |
| LCD custom glyphs and busy reads | Unsupported; ASCII text, commands, addressing and normal four-bit initialization supported. |
| Other chip/board peripherals | Unsupported, per requested non-goals. |
| GCC/Arm Compiler 6 compile adapters | Unsupported; use installed ARM Compiler 5 or upload HEX. |

Original uncorrected PDF samples with syntax errors remain uncompilable until
corrected. See [BOARD_NOTES](BOARD_NOTES.md) for every known correction applied
to the separate references and for mapping evidence.
