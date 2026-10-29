# LPC1768 hardware-fidelity test report

Audit date: 2026-10-29. Target: ALS-SDA-ARMCTXM3-01, ESD Labs 6–11.

**Assessment:** substantially stronger verification of the implemented digital
subset, with important remaining physical and timing limits. No physical board
was connected. Passing software tests does not certify complete LPC1768 or
physical-board equivalence.

## Execution results

The original repository baseline at `5069731bab7ab6e45c917cca8d43eb342abd13ec`
passed **129 backend tests and 29 browser tests**, with **zero failures**. The
TypeScript/Vite build passed. Backend baseline time was 133.39 seconds; its
record is `build/audit-baseline.xml`.

The final consolidated run passed **557 backend tests and 29 browser tests**:
**586 automated cases, zero failures, zero errors and zero skips**. The frontend
build also passed. It finished at **2026-10-29 06:08:09 UTC**. Backend execution
took 480.443 seconds, browser execution 50.530 seconds, and the build 2.863
seconds. The final calculator evidence replay also passed all 200 expressions;
that repeat is not added to the unique case count.

Backend cases are pytest cases, including parametrized cases. Browser cases are
Playwright cases. Finite input vectors inside tests are counted separately.
Repeated local runs are not added together as new unique tests.

| Backend test module | Cases in final collection | Purpose |
|---|---:|---|
| test_adc_fidelity | 65 | Ideal transfer, timing, flags, burst, IRQs, signed LCD difference, negatives |
| test_calculator_exhaustive | 202 | 200 expressions, invalid/held inputs, MCU reset during entry |
| test_display_fidelity | 80 | LEDs, segment masks, LCD commands, matrix/diodes/ghosting, reset and routing |
| test_examples | 26 | Existing catalog firmware compilation and behavior |
| test_execution_fidelity | 10 | ARMCC O0–O3, startup/data/stack/arithmetic, GPIO open drain, 3 MHz profile |
| test_exercise_requirements | 6 | One-second counters, complete catalog ring cycles, dice IRQ and 0–6 range |
| test_firmware | 15 | Existing compiled MMIO/IRQ/HEX tests |
| test_gpio_fidelity | 17 | Seeded latch/mask/width oracle, pin modes, full counter periods |
| test_jumper_routes | 1 | Alternate JP4 route |
| test_manual_connectivity | 38 | Existing literal manual pin maps and peripheral wiring |
| test_mutations_fidelity | 23 | 21 bad programs/configurations and two standalone positive controls |
| test_pwm_fidelity | 25 | Electrical waveforms, shadow latches, counter phase, flags, gates and seeded events |
| test_pwm_keypad | 6 | Keypad-controlled duty through a separate header |
| test_realtime | 24 | Clock dividers, timers, IRQs, wall-time counter and pause |
| test_runtime | 13 | API/worker/reset/validation behavior |
| test_user_calculator | 6 | Standalone F-equals/E-restart calculator with timer delays |
| **Backend total** | **557** | **428 added cases over the 129-case baseline** |

## Independently specified finite sweeps

| Input space | Enumerated observations | Expected-result source |
|---|---:|---|
| Eight LED states through each of four GPIO headers | 1,024 | Literal board pin tables and active-high bit mapping |
| All eight-bit segment masks on each digit | 1,024 | CNA2 segment order and CNB2 BCD selection |
| Sixteen keys × four row polls × all 24 scan orders | 1,536 | Literal matrix coordinates and column reads |
| Three-key rectangles and each scanned row | 576 | Schematic row-isolation diodes and passive key connectivity |
| All single-digit operand pairs, addition/subtraction | 200 | Python integer arithmetic; actual firmware LCD text observed |
| Seeded GPIO transactions, 500 per port | 2,500 | Separate latch/mask/access-width oracle |
| Bonded-pin direction/mux/pull observations | 280 | NXP pin behavior on 70 package pins |
| Eight-bit up/down/ring/reverse/Johnson periods and reversals | 1,098 | Independent integer/bit transitions |
| Four-digit decimal/hex carry, borrow and wrap boundaries | 15 | Literal expected values and manual glyphs |
| Requested PWM levels, two sampled periods each | 9 waveform records | Independent clock/level measurements; 18,000 sampled pin levels |
| Seeded PWM writes, latch enables and time advances | 256 | Independent integer counter/latch oracle, seed 176824 |
| Actual catalog 16-position ring, two cycles plus initial state | 33 | Independent one-hot physical segment-mask trace |
| ADC centers, all 4,096 codes on both channels | 8,192 | NXP ideal transfer step centers |
| Both sides of all 4,095 ADC thresholds, both channels | 16,380 | Lower/upper integer expectations at documented transitions |
| **Verified per-vector ledger total** | **33,123** | Excludes ordinary assertions and repeated runs |

The ledgers contain **8,551 digital/display/PWM records plus 24,572 ADC records**,
all with PASS observations in their documented ideal/model scope. PWM constant outputs at 0%
and 100% have no measurable edge frequency; the configured period is checked
separately. No fictitious frequency is inferred from constant HIGH/LOW samples.
All timing measurements here are simulated clock observations, not oscilloscope
measurements of the user's board.

## Initial failures and proof that regressions detect defects

The existing baseline's failure count was **0**. Existing green tests were
insufficient to establish hardware fidelity.

The archived first executions of the newly added checks contained the following
failures. These are separate batches, not a single pre-change full-suite run;
several failing cases identify the same defect. They are not a count of bugs.

| Archived initial evidence | Failed cases | Meaning |
|---|---:|---|
| build/audit-adc-before.xml | 33 | First 48 new ADC cases: 33 failed, 15 passed |
| build/audit-pwm-before.xml | 16 | Missing pin waveform, immediate latches, wrong active period and missing flags |
| build/audit-pwm-readback-before.xml | 1 | Alternate-function FIOPIN read used the GPIO latch |
| build/audit-execution-before.xml | 9 | Five open-drain assertions; four missing optimization-API errors |
| build/hardware-audit/display-initial.xml | 13 | LCD state and keypad isolation defects |
| build/hardware-audit/reset-initial.xml | 2 | MCU reset wrongly recreated the external LCD |
| build/hardware-audit/decoder-pullups-initial.xml | 5 | Missing decoder pullups falsely selected a digit |
| build/audit-pwm-pad-before.xml | 2 | PWM open drain and external-count false brightness |
| build/audit-pwm-one-based-before.xml | 1 | PWM counter reset-to-one requirement |
| build/audit-dice-range-before.xml | 1 | Reference emitted 1–6 instead of the explicit 0–6 requirement |
| **Recorded first-batch failures** | **83** | **79 behavioral failures plus four absent test-support API errors** |

The three counter timer requirements and dice interrupt requirement also failed
before the example corrections; those four initial failures were recorded in
console output rather than a separate initial XML. Additional ADC red/green
logs document refinements; they are not added to the table's fixed batch count.

For reproducible raw failure evidence, the audit also extracts the original
Git snapshot into `build/hardware-audit/original-replay/snapshot`, without
changing the current source or branch. **All 41 selected regressions failed
against that original model**, with zero collection/runtime errors. The replay
saves actual registers, GPIO/device state, firmware HEX hashes/files and the
last 128 MMIO operations in `original-replay/evidence/cases.jsonl`.
These expected historical failures are separate from final regression results.

## Fixed model defects: 24 documented groups

Counts below group related corrections by hardware behavior. They are not
24 unique physical measurements or one bug per failed parameter.

| ID | Corrected behavior | Regression evidence |
|---|---|---|
| ADC-01 | Ideal 4,096-step scale and half-LSB transitions | All nominal and threshold-side vectors |
| ADC-02 | Completion after 65 divided ADC clocks | Before/after completion, all PCLK selections and divider boundaries |
| ADC-03 | Hardware START settings no longer cause an immediate conversion | External-start and invalid burst/start negatives |
| ADC-04 | Burst scanning advances in time and channel order; clearing BURST finishes the in-flight conversion | Scan/stop/large-gap phase checks |
| ADC-05 | ADCR/global/channel DONE and independent read side effects | Repeated and mixed result-register reads |
| ADC-06 | Burst overrun generation, stickiness and clearing | Global/channel and subsequent-conversion checks |
| ADC-07 | ADSTAT DONE/overrun/interrupt fields | Independent nondestructive status checks |
| ADC-08 | Interrupt selection/acknowledgement and correctly serviced one-shot behavior | Actual C ISRs, plus an intentional unacknowledged IRQ storm |
| ADC-09 | Documented control/interrupt/trim reset values and locked trim bits | Reset and masked-write probes |
| PWM-01 | Shadow match writes and LER wait for the cycle boundary; active MR0 controls the current period | Mid-period duty/period changes and omitted LER |
| PWM-02 | Match channels 4–6 participate in match actions; their IRQ flags occupy bits 8–10 | MR4 W1C/IRQ regression and generalized match dispatch |
| PWM-03 | Missing MR0 reset no longer reports a fictitious periodic duty | No-reset negative and measured pin levels |
| PWM-04 | FIOPIN reads the PWM pad level instead of the GPIO output latch | Readback at HIGH/LOW edges |
| PWM-05 | TC uses the documented one-based PWM cycle without shortening the period | Four-clock counter/pin trace, two complete periods |
| PWM-06 | PINMODE_OD also releases a PWM HIGH; released pad cannot source LD10 | Pad/brightness regression |
| PWM-07 | Unsupported external-count mode does not claim periodic PWM brightness | CTCR negative case |
| GPIO-01 | Open-drain HIGH releases GPIO outputs | Five-port independent pin checks |
| LCD-01 | Clear restores increment mode | GPIO-driven clear/write sequence |
| LCD-02 | Return-home accepts its don't-care low bit | 0x02/0x03 behavior |
| LCD-03 | DDRAM and cursor moves wrap across the valid two-line address ranges | Forward/reverse edge writes and cursor commands |
| LCD-04 | Entry-mode display shifting and CGRAM address wrapping | Exact rendered rows and CGRAM isolation |
| KEY-01 | Row-isolation diodes prevent an inactive LOW row sinking an active HIGH row | Same-column multi-key and rectangle tests |
| SEG-01 | Documented decoder-input pullups disable or redirect undriven selection lines | All inputs and each single undriven address bit |
| RESET-01 | MCU reset/load retains the separately powered LCD's DDRAM and nibble phase | Reset during entry/partial nibble and subsequent reinitialization |

The audit additionally adds observable single-edge PWM pin levels and compiler
optimization selection for verification. Those capabilities are not counted as
extra original defects. The reviewed PWM counter phase agrees with UM10360's
reset value and an independently reported register experiment; exact startup
phase remains unverified on this user's board.

## Corrected reference firmware: seven groups

1. BCD up/down: replace the erroneous 4 ms setting with a derived 1-second timer.
2. Hex up/down: the same one-second requirement, checked independently.
3. BCD down: use Timer0 instead of a software scan counter.
4. Dice: service falling-edge EINT2 instead of polling SW2.
5. Dice: follow the manual's explicit 0–6 range, including zero.
6. Both ADC references: choose a legal ADC clock with the installed 100 MHz startup.
7. Both ADC references: disable internal pulls on the analog pins.

The generator preserves these changes. A punctuation-encoding regression found
during review was also corrected; it is not counted as an original hardware bug.
Original PDFs remain unchanged. The lab manual's separate 3 MHz clock profile can
use CLKDIV=0; that setting is not intrinsically incorrect.

Older positive PWM test programs omitted MCR reset-on-match. They now configure
actual periodic PWM. An older ADC probe assumed instantaneous completion; it
now polls DONE. The 2.475 V expectation changed from 3071 to 3072 using the NXP
ideal transfer, not to accommodate a convenient implementation output.

## Mutation campaign

**28 explicitly named mutants are detected out of 28 executed: 100% for this
finite campaign.** This is not a claim about arbitrary incorrect firmware.

| Family | Mutants | Detection |
|---|---:|---|
| LED mask, shift, port, direction, mux and missing cable | 6 | Intended physical LED pattern differs |
| Invalid seven-segment selector codes | 4 | No valid digit lights |
| PWM wrong match, power, output enable, reset and omitted latch update | 5 | Intended periodic brightness/updated waveform is absent |
| LCD reversed nibbles, missing E and wrong RS | 3 | Intended text does not appear |
| Counter rollover, wrong keypad row scan and missing LCD data jumper | 3 | Actual register/pin/render result differs |
| ADC power, mux, channel, PDN, START and missing DONE polling | 6 | Wrong sample or no valid completion |
| ADC per-channel IRQ with incorrect global-register acknowledgement | 1 | Repeated service exposes the unacknowledged flag |

Positive controls establish that the corresponding correct firmware works.
There are no surviving mutants in this named campaign. LCD timing, PLL feed,
unmodeled peripheral operations and analog electrical errors are outside this
mutation denominator and remain explicit false-positive risks.

## Coverage by lab and remaining limitations

| Lab | Established scope | Material remaining limit |
|---|---|---|
| 6 | All LED patterns/routes, switch levels, cable and GPIO behavior | SW2 physical pin ambiguity; software-loop wall time |
| 7 | Full 8-bit up/down/ring/reverse/Johnson periods and reversal, reference interaction | Mechanical bounce and every temporal interleaving |
| 8 | All masks/digits, decoder gates, carry/borrow/wrap, one-second timer/reversal, full catalog ring trace | Photometric persistence/flicker; full large catalog counter cycles |
| 9 | Stateful LCD commands, all scan orders, diode/ghost paths, 200 expressions, reset and IRQ dice | Busy/setup/hold timing, custom glyph rendering, contrast, calibrated randomness |
| 10 | Both ideal channels, every code/threshold side, timing/flags/burst/IRQs and signed LCD differences | Analog accuracy/aperture, floating inputs, external triggers/DMA |
| 11 | Requested duties, sampled high/low/period, latches/flags/gates and keypad control | Optical brightness, double-edge/other pads, host IRQ throughput |

All 19 manual entries appear in COVERAGE_MATRIX.md. No whole-exercise PASS is
inferred solely from compiling or booting a reference file.

HARDWARE_FIDELITY_GAPS.md defines **eight UNVERIFIED evidence groups** and **nine
UNSUPPORTED capability groups**. These are not skipped pytest tests. Important
risks before the exam are the actual SW2 route, 3 MHz versus 100 MHz startup,
LCD timing that this parser accepts too readily, and host-limited CPU/interrupt
throughput. PCGPIO gating and PLL feed validation are also incomplete, so some
invalid power/clock programs can falsely succeed. Full physical accuracy remains
unverified.

## Exact rerun commands

From the repository in PowerShell, using the installed Keil toolchain:

```powershell
.\.venv\Scripts\python.exe tools/run_hardware_audit.py
```

This runs all backend tests, builds the UI, starts an isolated service on port
8886, runs browser tests against it, then terminates that service. It does not
change the running user's service on port 8765. Port 8886 must be free; choose
another with `--port 8887`. For backend-only verification:

```powershell
.\.venv\Scripts\python.exe tools/run_hardware_audit.py --backend-only
```

To reproduce the deliberately failing original-model checks with raw traces:

```powershell
.\.venv\Scripts\python.exe tools/replay_hardware_regressions.py
```

That command succeeds only when its selected historical regressions expose
failures without test errors. Its failed assertions are intentional and are
never included as failures in the current simulator's result totals.

## Evidence and provenance

* `HARDWARE_SPEC.md`: exact PDF names, hashes, source hierarchy, registers, pins,
  connectors, jumpers, electrical assumptions and architecture.
* `COVERAGE_MATRIX.md`: all 19 samples/exercises/additional exercises and scoped evidence.
* `docs/ADC_AUDIT.md`: NXP ideal transfer figure, source hashes and detailed ADC evidence.
* `build/hardware-audit/summary.json`, `backend.xml`, `browser.xml` and logs:
  executable commands, environment, elapsed run times and automated outcomes.
* `build/hardware-audit/cases.jsonl` and `firmware/`: per-case register/device state,
  bounded MMIO traces and exact HEX hashes/files.
* `build/hardware-audit/display-vectors.jsonl`: individual digital/display/PWM vectors.
* `build/audit-adc-cases.jsonl`: 24,572 separate ADC observations with voltages,
  timing, configuration, expected/observed codes and source/confidence.
* `build/hardware-audit/original-replay/`: isolated original source, expected failures
  and raw failing traces, distinct from final passing evidence.
* `test-results/hardware-audit/`: browser-render evidence regenerated by Playwright.

Sources include the two supplied local PDFs; NXP UM10360 Rev.2 chapters 8, 9,
21, 24 and 29; the NXP LPC176x datasheet Rev.9.10 Fig.28; the HD44780U controller
reference for the modeled compatible instruction set; and installed NXP CMSIS
headers/startup. Device identity, analog behavior and physical timing that these
references do not settle remain explicitly unverified.
