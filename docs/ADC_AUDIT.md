# Lab 10 ADC audit

The simulator now has a timed, ideal ADC model for the two documented board
inputs. This is document-backed digital/register verification, not a measurement
of an LPC1768 board. Physical accuracy, analog noise, and acquisition behavior
remain unverified.

## Sources and board wiring

Both supplied PDFs were extracted in full using the global Python installation
and PyMuPDF, with UTF-8 output. Relevant ADC evidence is:

| Source | Evidence |
|---|---|
| `ESD.pdf`, PDF pp.45–47 (printed 41–43) | AD0.4/P1.30/POT4, AD0.5/P1.31/POT1; 0–3.3 V; 12-bit range; JP18(2–3); ADC difference displayed on LCD |
| `ARM_LPC-1768_User_Manual (1).pdf`, PDF pp.33–34 and 51 | Same direct board connections and JP18 requirement; no FRC cable is required for either ADC input |
| Board manual PDF pp.46–47 | Laboratory startup configuration: 12 MHz oscillator /4, PLL disabled, 3 MHz CPU, PCLK=CCLK |
| [NXP UM10360 Rev.2, chapter 29, pp.574–581](https://www.pololu.com/file/0J431/user.manual.lpc17xx.pdf) | Register map/reset values, 65 ADC clocks, PCLK/CLKDIV, power, start modes, burst scan ordering, read side effects and interrupts |
| [NXP LPC176x data sheet Rev.9.10, Fig.28, PDF p.68](https://www.nxp.com/docs/en/data-sheet/LPC1769_68_67_66_65_64_63.pdf) | Ideal half-LSB transition positions and 1 LSB=(VREFP−VREFN)/4096; actual curves differ from the ideal |

The NXP documents are downloaded under `build/UM10360.pdf` and
`build/LPC176x_datasheet.pdf`. The transfer figure was rendered and visually
inspected as `build/ADC_transfer.png`; text extraction alone does not establish
the half-LSB transition positions.

SHA-256 fingerprints, in the source order ESD, board manual, UM10360, data sheet:

```text
9B93D75FC0C1815AC02127DDB522D52C3B643C7FA298ECB8D5F07A095EEBF97B
06E5BEC536F259B1D409A0768E22478553C03BF0FEB3B7D8FFDC9F7DD49C7BB7
ECF8947A8B4837822798F1CD21183D5AC094B4E0D516C98119C5E33CF9A29740
DC8A0FFFE9859BD5A4AF4A2DD865BB11BC594A932F06722FBA5BAF579F16E54F
```

## Independent quantization oracle

The old `round(V/3.3*4095)` model did not reproduce Fig.28. An ideal step is
3.3/4096 V wide. Step centers are integer multiples of that width, and transition
from code k−1 to k lies at (k−0.5) LSB. Production conversion uses a saturated
nearest-integer conversion with half ties directed upward. The exact tie choice
is a deterministic convention; it is not asserted as a physical comparator rule.

Tests construct voltage at the documented center for each expected integer code;
they do not call, import, or reproduce the production conversion function to
calculate expectations. Threshold tests explicitly expect the lower or upper
integer on either side of every transition. Their displacement is 0.00001 LSB
(about 8.06 nV), useful only for ideal mathematics. Real board thresholds cannot
be predicted to that tolerance from the supplied documents.

Both channels independently cover:

| Sweep | Per channel | Total |
|---|---:|---:|
| All nominal code centers, 0 through 4095 | 4096 | 8192 |
| Below and above all 4095 transitions | 8190 | 16380 |
| Enumerated ideal input observations | 12286 | 24572 |

The final sweep emits `build/audit-adc-cases.jsonl`: one record per input, with
case ID, lab, voltage, channel, ADCR, PCLK divider, elapsed core clocks, wiring,
expected/observed code and register, status, source, and confidence. These 24,572
observations are **not** counted as 24,572 pytest tests. The general audit fixture
also saves bounded MMIO traces, original registers, final device state, firmware
HEX files and hashes under `build/hardware-audit/`.

## Regression evidence

The original selected tests passed before production changes:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_manual_connectivity.py -k adc tests/test_firmware.py tests/test_examples.py
```

Result: **5 passed, 74 deselected**. The first new independent batch then ran
against the unchanged engine: **33 failed, 15 passed** (48 tests). Evidence is
`build/audit-adc-before.xml` and `build/audit-adc-before.log`.

The initial sweeps found 2047/4096 wrong nominal results per channel and
4095/8190 wrong near-transition results per channel: **12,284 incorrect results
out of 24,572 input observations**. The first failing center was code 2049;
the old model returned 2048. A point just above the first ideal transition
returned 0 instead of 1.

Additional tests were added while implementing timing and integration; separate
red/green evidence covers power-change accounting, the final in-flight burst
conversion, sticky overrun, correct ISR acknowledgement, and example pull modes.
The initial 33 failures refer to the original 48-case batch, not a hypothetical
baseline run of tests that did not yet exist.

Final command:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_adc_fidelity.py tests/test_manual_connectivity.py tests/test_firmware.py tests/test_examples.py -k adc --junitxml=build/audit-adc-final.xml
```

Final result: **70 passed, 74 deselected**, comprising 65 new ADC tests and 5
selected existing tests. No ADC tests are skipped or marked expected failure.
See `build/audit-adc-final.xml` and `build/audit-adc-final.log` for execution data.

## Corrections and implemented scope

The nine engine defect categories below are distinct from the two firmware
configuration corrections. Refinements discovered during implementation are
included in their corresponding category, not counted again as original bugs.

| ID | Correction | Independent check |
|---|---|---|
| ADC-01 | Correct ideal quantization scale and rounding | 8192 nominal and 16380 boundary observations |
| ADC-02 | Conversion completes after 65 divided ADC clocks, not inside ADCR write | All four PCLK selections × CLKDIV 0,1,7,255, reads before/after completion; real-time pause/resume |
| ADC-03 | START=2–7 arms hardware start without immediate conversion; BURST+nonzero START does not begin | Six external-start negative cases and invalid burst/start case |
| ADC-04 | Burst advances with elapsed time, ascending channels, one conversion per interval; clearing BURST finishes the current conversion | Phase/order/stop tests; a 10^12-core-clock jump preserves phase without iterating billions of conversions |
| ADC-05 | ADCR write clears global DONE; reads clear only their corresponding data-register status | Independent global/channel and repeated-read probes |
| ADC-06 | Burst overrun is generated, stays sticky, and clears on the relevant data-register read | Global/channel overrun tests, final in-flight burst and subsequent single-shot tests |
| ADC-07 | ADSTAT includes per-channel DONE and OVERRUN and ADC interrupt status | Nondestructive status read and flag mirroring checks |
| ADC-08 | Global interrupt selection takes precedence over individual enables; level requests persist until acknowledged without duplicating a correctly serviced one-shot IRQ | Executed C handlers using GDR/global mode and ADDR5/channel mode; intentional mixed-read interrupt storm |
| ADC-09 | ADCR/ADINTEN/ADTRM documented reset values; boot TRIM bits remain locked | Reset and offset-register write/read tests |
| ADC-FW-01 | Both corrected Lab 10 examples use CLKDIV=1 at installed compiler's 100 MHz startup | Executed firmware register inspection: 25 MHz PCLK /2 =12.5 MHz ADC ≤13 MHz |
| ADC-FW-02 | Both corrected Lab 10 examples disable pulls on P1.30/P1.31 | Executed firmware PINMODE3 readback per UM10360 29.6.3 |

Power gating, PDN, analog pin function, and JP18 remain part of the supported
input path. Channel 5 is independent of JP18. Static result data remains readable
after DONE is cleared and does not resample when single-shot data is read again.

The previous connectivity fixture assumed an immediate result. It now polls
DONE into a local variable before writing its SRAM observation mailbox; powered
off paths still observe no completion. The expected 2.475 V result changed from
3071 to 3072 based on Fig.28, not to accommodate an implementation choice.

The original ESD p.46 sample polls equality with `0x80000000`, rather than testing
the DONE bit. Channel bits and result bits make that equality unsuitable. The
simulator does not repair this firmware error. Corrected examples use bit tests.

CLKDIV=0 in the manual is compatible with its separate 3 MHz startup guidance;
it is not inherently wrong. It was wrong for full-resolution conversion with
the repository's installed 100 MHz CMSIS startup. Corrected examples explicitly
choose a safe ADC clock for that profile.

## Compiled firmware and mutations

Keil compiles the probes to Cortex-M3 HEX, and Unicorn executes every MMIO access.
There is no source-name recognition or direct firmware-result injection.

* 18 explicit voltage/channel checks cover 0,0.1,0.5,1.0,1.65,2.0,2.5,3.0,3.3 V.
* 100 deterministic random nominal-code reads switch channels using seed 1768.
* Nine signed difference cases check the actual complete 16-character LCD line:
  equal inputs, both endpoints, both positive/negative extrema, and either channel
  held at midscale while the other varies.
* Six deliberately wrong C probes omit power, analog mux, PDN, START or polling,
  or select the other channel. **6/6 are detected**, with a separate correct
  control passing.
* A seventh mutation uses per-channel IRQ enable but reads GDR in its ISR.
  **1/1 is detected** by repeated service of the unacknowledged channel DONE.
  Correct global/GDR and channel/ADDR5 variants each service a single IRQ.

## Unsupported and unverified behavior

| Status | Behavior and consequence |
|---|---|
| UNVERIFIED | No real-board voltage sweep, oscilloscope conversion timing, reference measurement or noise characterization was available. Passing ideal tests cannot certify physical ADC accuracy. |
| UNVERIFIED | The model samples voltage when conversion begins. Exact acquisition aperture, source impedance, settling, sample capacitor retention and changes during acquisition are not physically modeled. |
| UNVERIFIED | JP18 open/1–2 and digital-mux ADC reads use deterministic zero. This preserves a visible wiring/configuration failure; real floating/USB-related voltages are not guaranteed zero. |
| UNVERIFIED | ADC pin pulls are writable but do not load the analog potentiometer model. Corrected examples disable pulls. An otherwise incorrect program can obtain an ideal value despite pull-induced physical error. |
| UNVERIFIED | UM10360 Table532 describes a restart on ADCR write during conversion, while 29.6 says new launches are ignored until completion. The model follows 29.6; resolve against actual silicon/errata before depending on busy-write behavior. |
| UNVERIFIED | Changing clock dividers/power/mux during acquisition has no validated silicon-level transient model. Completed work is accounted before SC changes; active conversion edge phase and abort transients are approximate. |
| UNVERIFIED | FIOPIN reads from analog-selected pins are invalid according to UM10360 9.5.6. Existing digital GPIO behavior is not a supported analog readback promise. No arbitrary zero-read rule was introduced. |
| UNSUPPORTED | External pin/timer ADC start edges are not connected to the ADC trigger engine. START=2–7 now correctly avoids a false immediate conversion, but actual edges do not start a conversion. |
| UNSUPPORTED | ADC DMA, offset-trim effects on conversion, analog error/noise, variable VREF and channels other than wired AD0.4/AD0.5. Unsupported channels produce an explicit firmware error. |
| UNSUPPORTED | Accurate analog results above the documented ADC clock limit. The deterministic model continues to calculate ideal codes and does not manufacture an overclock noise/error model. |
| APPROXIMATE | Offline time derives from executed basic-block size, not instruction-accurate Cortex-M3 cycle timing. Live time derives from the paused/running monotonic clock. |

Exact ties, floating inputs, analog-selected digital readback and active-conversion
electrical transients are intentionally not presented as independently verified
physical pass cases.
