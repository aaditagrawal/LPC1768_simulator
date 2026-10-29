# Lab6–11 hardware coverage matrix

Audit sources and page-number convention are in `HARDWARE_SPEC.md`. This is an
inventory of **every sample, exercise and additional exercise actually printed
for Labs6–11** in the supplied65-page ESD PDF: **19 entries**. The18-entry UI
catalog omits the keyboard-PWM exercise, which has a separate standalone source.
The request's additional reverse/Johnson/boundary cases are tracked below; they
must not be misrepresented as extra questions present in this manual edition.

`PASS` means the identified tests observed the independently specified behavior
within the stated scope. `FAIL` means an observed contradiction. `UNVERIFIED`
means evidence or verification is insufficient; `UNSUPPORTED` means absent
implementation. Passing compilation/boot alone is never whole-exercise PASS.
The final run and totals are recorded in `TEST_REPORT.md`; where a whole exercise
has broader requirements than the tests, its row remains scoped/UNVERIFIED.

## Complete manual inventory

| ID | ESD PDF page (printed) | Kind and exact intent | Required hardware | Source / verification and present limit |
|---|---|---|---|---|
| L6-E1 | 27 (23) | Blink an LED | GPIO output, active-high LED, ribbon, executed delay | `lab6_blink.c`; GPIO/256-pattern and example tests. Uses all8LEDs. Blink wall-time is host-dependent: **UNVERIFIED timing**. |
| L6-E2 | 27 (23) | P2.12 switch pressed→LED on; released→off | SW2 lab profile, CNB→CNB1, CNA→CNA1 | `lab6_switch.c`; real firmware switch/route/disconnect tests. Pin7 versus pin9 physical routing remains **UNVERIFIED**. |
| L7-S | 28–29 (24–25) | Serial LED ON then OFF | FIOSET/FIOCLR preserve neighbors, GPIO delay | `lab7_sequence.c`; tests observe1→3→7; unfamiliar generated register/counter tests check full periods. Original sample syntax corrected separately. **UNVERIFIED physical delay**. |
| L7-E1 | 29 (25) | 8-bit binary up counter | 8LEDs, unsigned wrap, GPIO | `lab7_binary.c`; full256-state periods/boundaries in `test_gpio_fidelity.py`, all256output patterns per header. |
| L7-E2 | 29 (25) | SW2-controlled8-bit up/down counter | GPIO input and output, correct wire route | `lab7_updown.c`; generated up/down full-period/reversal and reference switch tests. Catalog program's full temporal sequence is **UNVERIFIED** separately from the underlying hardware tests. |
| L7-A3 | 29 (25) | 8-bit ring counter with SW2 keypress | One-hot rotate, switch edge/hold, LED mapping | `lab7_ring.c`; reference advances1→2→4→8 on separate presses and holds; generated ring/reverse tests execute full periods twice and reverse. Debounce/bounce tolerance is **UNVERIFIED**. |
| L8-S | 32–35 (28–31) | Four-digit BCD up counter | U7 BCD digit address, U12 segments, multiplex, software delay | `lab8_bcd_up.c`; all256masks×4digits, decimal boundaries and example boot. Sample timing is a software approximation. Full0→9999catalog cycle **UNVERIFIED**. |
| L8-E1 | 35 (31) | Four-digit BCD up/down with switch and **1-second timer** | Timer0, seven-segment scanning, alternate SW2 header | `lab8_bcd_updown.c`; `test_exercise_requirements.py` checks emitted digits before999ms/after1001ms, live reversal,0→9999→0. **Fixed:** prior4ms timer. Physical SW2 ambiguity/timing limits remain. |
| L8-E2 | 35 (31) | Four-digit binary ring counter |16-bit rotation and raw segment masks, multiplex | `lab8_ring.c`; the actual catalog program's 16-position physical mask trace passes two full periods. Photometric rendering remains approximate. |
| L8-A1 | 36 (32) | Four-digit BCD down counter, **use timer for delay** | Timer0, decimal borrow/wrap, multiplex | `lab8_bcd_down.c`; **fixed** to use1-second Timer0 instead of20software scans; requirement regression checks9999→9998. Complete catalog countdown remains **UNVERIFIED**. |
| L8-A2 | 36 (32) | Four-digit hexadecimal up/down with switch and **1-second timer** | Timer0, hexadecimal glyphs, wrap, alternate SW2 route | `lab8_hex_updown.c`; same virtual-time/reversal test plus independent hexadecimal boundary/glyph cases. **Fixed:** prior4ms timer. |
| L9-S1 | 39–41 (35–37) | Display fixed message on16×2 LCD | CND→CNAD, JP5/16, four-bit initialization, E/RS, DDRAM | `lab9_message.c`; exact lines, spaces/overwrite/off-screen/commands and malformed transaction tests. LCD busy/timing correctness remains **UNSUPPORTED**. |
| L9-E1 | 41 (37) | DIE tossing on LCD, SW2 **external interrupt**, random0–6 | EINT2, SW2, LCD | `lab9_dice.c`; **fixed** polling→falling-edge EINT2 and range→0–6. Tests check IRQ entry/return, repeated edges, no held-edge repeat, and all seven values across 32 press phases. Random distribution remains **UNVERIFIED**. |
| L9-S2 | 42–44 (38–40) | Read matrix key, display0–F identity on LCD or7seg | CNB3 rows/columns, JP4, LCD/7seg | `lab9_keypad.c`; all 16 keys × 4 rows × 24 orders, holds/releases, row diodes and 576 ghost rectangle observations. LCD output tested; keypad→7seg queue is not a separate printed exercise and remains **UNVERIFIED**. Original sample has wrong registers and missing functions. |
| L9-E2 | 44 (40) | Input A operator B =; operands0–9, +/−, result onLCD | Key scanning/debounce policy, signed arithmetic, LCD | `lab9_calculator.c`; `test_calculator_exhaustive.py` enumerates **200complete expressions**, exact LCD text, zero/negative/two-digit results, invalid/missing-equals/held/clear cases. `calculator_timer.c` has a different documented F=equals/E=restart key policy with live tests. |
| L10-S | 45–47 (41–43) | Read AD0.5 and display digital/analog voltage onLCD | POT1/P1.31function3, ADC power/clock, conversion, LCD | `lab10_adc5.c`; all4096ideal code centers and8190threshold-side cases **per channel**, ADC timing/control tests and LCD integration. Analog calibration/noise are **UNVERIFIED**. Original sample's DONE loop is incorrect. |
| L10-Ea | 47 (43) | Display digital difference between AD0.4 andAD0.5 | POT4/JP18, POT1, sequentialADC, signed subtraction, LCD | `lab10_difference.c`; ADC independence, signed/extreme/equal-input and LCD evidence in `test_adc_fidelity.py`; no simultaneous sampling assertion. Physical analog error remains **UNVERIFIED**. |
| L11-S | 48–50 (44–46) | Vary LD10 intensity using PWM interrupt | PWM1.4/P1.23, MR0/MR4, LER,IRQ9, CNB→CNB1 | `lab11_pwm.c`; PWM pin high/low/frequency, latch timing, flags, gates, sweep-handler evidence. LED optical brightness/TP6 analog output remain **UNVERIFIED**. |
| L11-E | 50 (46) | ROW0 keys0/1/2/3 select10/25/50/75% | PWM+keyboard concurrent, separate ribbon/header | Standalone `pwm_keypad_timer.c`; allfourlevels, holds/releases/repeats, other-row rejection, JP5/cable gating and browser interaction. Not listed in UI catalog; electrical support is separate from catalog availability. |

No additional exercise block is printed in Lab6,9,10or11 in this edition.
Lab7 labels its additional ring exercise “3”; that numbering is preserved here.
Lab8 has two separately printed additional exercises. The mbed section after
Lab11 (PDFpp51–55) targets a different LPC1768 prototyping board and is outside
the requested ALS Labs6–11 scope.

## Hardware capabilities and additional requested test spaces

| Capability / requested finite space | Independent evidence / test location | Scope and remaining distinction |
|---|---|---|
| All256LED patterns on each of4GPIO headers | `test_display_fidelity.py`, compiled MMIO and literal bit oracle |1024pattern observations; all8mapped LED lines, disconnection and jumpers. Not photometric intensity. |
| GPIO write/mask/width/RMW invariants | `test_gpio_fidelity.py` |500seeded operations per port, byte/halfword/word accesses,5ports, valid-package-pin comparisons. Not an exhaustive32-bit state space. |
| PINSEL/pull/direction and input-latch preload | `test_gpio_fidelity.py`; `test_execution_fidelity.py` | Bonded-pin sweeps and open-drain regression; repeater mode and all startup/debug exceptions remain gaps. |
| Serial/binary/ring/reverse/Johnson transitions | `test_gpio_fidelity.py` | Full periods twice plus direction reversals for unfamiliar compiled programs. Busy-loop wall-time not calibrated. |
| Thumb arithmetic, initialized/BSS data, stack, optimization | `test_execution_fidelity.py` | ARMCCO0/O1/O2/O3, volatile MMIO, unsigned wrap/shifts and stack-local values; not an exhaustive ARM ISA differential suite. |
| Timer/PCLK/prescaler/fraction/pause/reset | `test_realtime.py`, `test_pwm_fidelity.py`, requirement tests | All4timer clock selectors, match/reset/stop/W1C/IRQ and host-gap batching; host CPU/IRQ throughput limits remain. |
| All256segment masks on each4digits | `test_display_fidelity.py` |1024settled display observations, dp/blank/all-on included. Renderer history shortened only in finite-space tests; live50ms persistence separately tested. |
| Digit selection codes0–15 | `test_display_fidelity.py`, `test_mutations_fidelity.py` |0–3positive,4–15negative. Documented decoder input pullups are tested; analog voltage competition remains unverified. |
| Decimal carry/borrow and hexadecimal wrap | `test_display_fidelity.py` | Listed0/9/99/999/9998/9999boundaries and0xFFFFwrap; no claim of all10000/65536counter states. |
| Live1-second multiplex and SW2 reversal | `test_realtime.py`, `browser-tests/realtime.spec.ts` | Actualtimer firmware at existing frontend cadence; visual slow-refresh/flicker/ghost current still approximate. |
| LCD command/data/addressing | `test_display_fidelity.py`, manual connectivity tests | Exact16×2text, two-line40-cell DDRAM boundaries, cursor/home/clear/entry shifts, displayoff/on, CGRAMaddress behavior. Busyflag/write timing and custom glyph rendering unsupported. |
| LCD bad GPIO mutations | `test_display_fidelity.py` | Missing E, reversed nibbles, wrong direction/mux, cable/JP5/JP16gates prevent intended output. Physical setup/hold timing mutations are not detected. |
| All16keys and scan-order permutations | `test_display_fidelity.py`, manual connectivity tests |All24 scan orders;1536key/row observations plus repeats/holds. Not every input-event schedule. |
| Multi-key electrical paths | `test_display_fidelity.py` | D6–D9row-isolation cases and allthree-key rectangle positions,576scan observations. Diode voltage drop/current are idealized. |
| Bounce, missed between-scan presses, deterministic event scheduling | Live user-calculator tests cover firmware debounce/hold/release | Controlled short/missed/held pulses are tested. No calibrated bounce model or general event queue is claimed. |
| All200calculator expressions | `test_calculator_exhaustive.py` |100pairs×2operators, actual keypad scanning/ARM arithmetic/LCD writes; policy belongs to tested program. |
| All4096ADC codes and allthreshold sides | `test_adc_fidelity.py` |2channels; nominal centers andbothsides of4095transitions; idealtransfer only, excludesexactties and physical error/noise. |
| ADC power/mux/channel/timing/DONE/overrun/burst | `test_adc_fidelity.py` | FinalADC audit model and negative controls; external-start/DMA/all8analogpins are not thereby established. |
| PWM0/1/10/25/50/75/90/99/100% | `test_pwm_fidelity.py` |2complete1000-clock periods per duty, actual output-level sampling; integer-clock frequency oracle. |
| Mid-period PWM latching / random schedules | `test_pwm_fidelity.py` |256seeded duty/latch/time changes and period-boundary tests. No claim for double-edge/allchannels. |
| PWMkeyboard integration | `test_pwm_keypad.py`, browser test and manual connectivity test | FourROW0levels, holds/releases, alternateCND/CNCroutes, JP5andcable negatives. |
| Mutation testing | `test_mutations_fidelity.py`, display/ADCnegative tests | Deterministic named defects with positive controls; **not a statistical claim** about all possible program mutations. Finaldetected/executedcounts inTEST_REPORT. |
| Runtime validation/reset/load/wiring preservation | `test_runtime.py`; browser suites | Atomic failedload, manualwiring, pause/resume, retainedpots/jumpers; no physicalbrownout/ISP simulation. |
| Cross-peripheral sharing | Calculator,ADC+LCD,PWM+keyboard,SW2+LED/7segtests | Tested combinations use physically possible one-cable-per-header routing. No automatic duplication/splitting. |
| Trusted/emulated/physical differential comparison | Document-derived integer/bit/transfer oracles | No second independent full ARMemulator run, oscilloscope capture, realboard trace or HIL fixture: **UNVERIFIED**. |

## Audit regressions and interpretation

`test_exercise_requirements.py` was executed before the example fixes and
observed **4failures**: early BCDup/down andhex updates, software-timedBCDdown,
and no external IRQ in dice. The same tests pass after the example corrections,
including boundary reversal and repeated/held SW2 cases. These are **4example
defects**, separate from peripheral-engine defects counted elsewhere.

Other audit additions include ADCtransfer/timing, PWMwaveform/latching and LCD/
keypad semantics. Use the recorded initial/final XML and per-stimulus ledgers in
`TEST_REPORT.md`; do not add loop iterations to pytest counts or combine repeated
runs into a misleading “unique tests” count.

The highest-confidence scope is compiled register/pin logic with documented
wiring and ideal device behavior. Physical timing/electrical equality remains
UNVERIFIED even when all corresponding software checks pass.
