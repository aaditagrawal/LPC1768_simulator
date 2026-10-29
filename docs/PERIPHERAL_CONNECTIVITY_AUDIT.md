# Peripheral connectivity audit — 29 October 2026

Historical pre-audit record: current results, corrected reference behavior and
coverage are in [TEST_REPORT.md](../TEST_REPORT.md),
[HARDWARE_SPEC.md](../HARDWARE_SPEC.md) and
[COVERAGE_MATRIX.md](../COVERAGE_MATRIX.md). The earlier results below are
retained for provenance and do not describe the current model.

Timing update after this audit: live timers/PWM now use elapsed time and
configured clock divisors. See [TIMING](TIMING.md) for the new implementation
and regression evidence. Timing limitations below describe the original audit.

The modeled lab peripherals pass the manual-derived GPIO connectivity checks
below. The simulator does **not** implement every peripheral in the board manual.
Drawn components, connectors and movable shunts do not establish functional
electrical or protocol models.

This audit checks software against the supplied documents; it does not certify a
physical PCB. No simulator implementation or reference firmware was changed.

## Sources and method

Sources: the local [board manual](../ARM_LPC-1768_User_Manual%20%281%29.pdf)
and [lab manual](../ESD.pdf). Page numbers below are **one-based PDF page
numbers**, not the printed page footers.

* Board: GPIO headers pp.24–26; LCD pp.31–32; ADC pp.33–34;
  LEDs pp.34–35; keypad, PWM/interrupt and seven-segment pp.36–37;
  test procedures pp.50–58.
* Lab: LEDs/SW2 pp.27–29; seven-segment pp.30–36; LCD/keypad pp.37–44;
  ADC pp.45–47; PWM pp.48–50; connector appendix pp.63–65.
* Fresh PDF text extracts: `build/board-manual-audit.txt` and
  `build/lab-manual-audit.txt`.

Backend probes compile C with the installed Keil compiler and execute the ARM
instructions. Expected pin numbers are transcribed independently of the runtime
mapping. An SRAM mailbox supplies stimulus/readback; firmware performs all GPIO,
ADC and PWM register accesses. Outputs are not substituted with expected values.

Browser checks use a separate simulator on `127.0.0.1:8876`, preserving the user's
firmware and physical setup on port 8765. They compile through the IDE, operate
keypad controls/sliders and inspect rendered SVG outputs as well as API state.

## Connectivity results

| Peripheral | Required connection/configuration | Result and evidence |
|---|---|---|
| LEDs LD2–LD9 | CNA → CNA1; P0.4–P0.11, active high | PASS: each line, all-on/off and alternating patterns; disconnect removes output. |
| Other GPIO port-line tests | CNB/CNC/CND → CNA1; JP4 1–2 / JP5 closed for their affected lines | PASS: all eight LED lines through each of all four MCU headers. Opening JP4 isolates CNB pin 8; opening JP5 isolates CND pin 4, leaving other lines usable. |
| SW2 GPIO input | CNB → CNB1; CNB1 pin 7 → P2.12 in lab profile | PASS for lab profile: press low/release high. Also passes via CNA/P0.10, CNC/P0.21 and CND/P2.0. Physical trace ambiguity remains; see below. |
| SW2 external interrupt | CNB → CNB1; P2.12 function 1/EINT2 | PASS: real handler toggles LD10, returns to main and does not repeat while an edge-triggered press is held. Existing tests cover level-triggered re-pending. |
| Text LCD | CND → CNAD; JP5 and JP16 closed; P0.23–26 = D4–D7, P0.27 = RS, P0.28 = E | PASS: four-bit initialization and exact two-line text. Initialization with a missing cable/jumper is not replayed after reconnecting; reset is required. |
| LCD disconnect/visibility | Same setup | PASS: disconnect retains contents and drops new writes; reconnect allows subsequent writes. JP16 hides/reveals retained text in the logical model. |
| Keypad | CNB → CNB3; JP4 1–2; P2.10–13 output rows, P1.23–26 input columns | PASS: all 16 keys, every row/column selection, no-key pulldowns and release; all 16 browser controls produce the corresponding LCD keycode. |
| Alternate keypad headers | Board p.36 / lab p.41 permit another GPIO header with corresponding firmware | PASS through CNA, CNB, CNC and CND. CND needs JP5 for column 4. JP4 open/2–3 disconnects only CNB's fourth row. |
| Seven-segment | CNA → CNA2 for segment bits; CNB → CNB2 for U7 BCD digit addressing | PASS: all eight bits, including decimal point, on all four digits; all 16 reference hex glyph patterns; either cable disconnect blanks output. Browser renders expected patterns for 1234. |
| POT1 / AD0.5 | P1.31 function 3; ADC power/PDN enabled; LCD setup for text | PASS: 0, 0.825, 1.65, 2.475, 3.3 V → 0, 1024, 2048, 3071, 4095 counts under simulator rounding. Wrong mux yields zero; powered-off ADC stops producing DONE. Browser slider/text verified. |
| POT4 / AD0.4 | P1.30 function 3; JP18 2–3 | PASS: same voltage sweep; JP18 open/1–2 disconnects POT4, 2–3 restores it. Browser verifies positive/negative ADC4−ADC5 differences and JP18 gating. |
| PWM1.4 / LD10 | CNB → CNB1; P1.23 function 2; PWM power/PCR/TCR/LER configured | PASS: 0%, 10%, 25%, 50%, 75%, 100%; mux/cable gating. Existing reference test checks interrupt-driven MR4 changes. Browser shows 25%, then 0% after disconnect. |
| Keypad-selected PWM | Lab p.50: row-0 keys 0–3 select 10%, 25%, 50%, 75% | PASS with test firmware: CNB → CNB1 and CNC → CNB3 avoid occupying CNB with two cables. Firmware scans CNC pins and controls PWM1.4. No additional built-in reference was created. |
| Timer0–Timer3 | Internal match/IRQ; GPIO LED provides handler evidence | PASS: each timer executes its real match handler and returns. Existing Timer0 tests cover stop/reset and multiple matches. This does not establish external capture/match routing or wall-clock accuracy. |
| Reset / simulator controls | Reset after connection/program loading | PASS in existing tests: reset preserves physical setup; pause/resume/stop and release of held inputs are exercised. |

## Board-manual features that are not implemented

These are absent capabilities, not failures of the passing connectivity tests.
Changing cables alone cannot make them functional.

| Feature | Manual setup | Simulator limitation |
|---|---|---|
| LCD contrast | POT3, board pp.31,50 / lab pp.41,44 | No contrast model; logical text visibility follows the LCD/JP16 state. |
| Graphic LCD | CNA → CNAD; CND → CND1; JP16 open, JP17 2–3, JP5 closed; p.50 | No controller or CND1 cable endpoint. JP17's shunt is visual only. |
| Relay, buzzer, DC/stepper motors | CNA → CNA5; CN12/RM5/PM1 as appropriate; pp.33,52 | CNA5 and these loads are not modeled. |
| DAC / CLKOUT | TP8 with JP5 open; TP9 with JP19 open; pp.34,51 | No DAC output or clock measurement model. |
| External capture/match | CNB → CNB1; JP14/RM4/TP4; pp.36–37,52 | CNB1 pins 3/4 and JP14 are not routed; capture and external-match waveforms are absent. Basic timer IRQ coverage does not cover this feature. |
| UART0/UART3 / RS485 | CN9/RM1 or CNC → CNC1; relevant jumper settings; pp.50,53 | Serial protocol/register models and CNC1 are absent. JP7/JP8/JP12/JP13 move only visually. |
| SPI EEPROM / I2C RTC / internal RTC | CNC → CNC1 and corresponding jumpers; pp.51–53 | Bus/device models and CNC1 are absent. |
| I2S | CNA → CNA4 and CN17 loopback; p.53 | I2S and CNA4 are absent. |
| CAN | JP7/JP8 2–3, JP9 and RM2 loopback; p.53 | Controllers/transceivers and loopback are absent. |
| USB device/host/OTG | SW19/SW20, JP18 and USB connectors; pp.53–57 | No USB enumeration or host/device behavior. JP18's implemented effect is POT4's ADC route. |
| Ethernet | CN13 and network setup; p.58 | Network controller absent; POT5's ADC route is not established. |
| Power / ISP / JTAG / test equipment | Power/programming jumpers and test points | No physical power circuit, boot-ROM ISP, Flash Magic transport, JTAG probe, oscilloscope or meter model. Local C compilation and HEX loading are available. |

Direct register probes rejected UART0/1/3, SPI/SSP0, I2C1, I2S, CAN1, DAC, RTC,
USB and Ethernet as unsupported. Attempts to connect CNA4, CNA5, CNC1 and CND1
were rejected. Exact results: `build/peripheral-unsupported-probes.json`.
These establish absence of a model, not protocol conformance.

## Qualifications and differences from the lab exercises

1. **SW2 manual conflict:** board p.37 lists CNB1 pin 9 as both NC and external
   interrupt; lab p.29 explicitly specifies pin 7. CNB pin 9 is NC in board
   p.25. The tested default follows the lab's pin-7 route. The alternative
   profile does not settle physical PCB truth.
2. **Keypad evidence:** row/column endpoint mapping follows lab p.43 and the CNB
   table. Board prose establishes row outputs and column pulldowns without
   independently enumerating CNB3 pins. The implemented mapping passes the tests.
3. **Timing:** instruction-derived logical timing does not certify the requested
   one-second intervals, PWM frequency or measured TP6 voltage. PWM checks prove
   duty ratio/visible brightness, not an oscilloscope waveform.
4. **Lab 8 BCD-down reference:** `examples/lab8_bcd_down.c` uses software
   scan-count delays; lab p.36 asks for a timer. Connectivity works, but this
   reference does not meet that timer requirement as written.
5. **Lab 9 dice reference:** `examples/lab9_dice.c` polls SW2 rather than using
   an external interrupt as suggested on lab p.41. It outputs 1–6; the page
   says 0–6. EINT hardware behavior is separately tested, but the reference is
   not an interrupt example.
6. **Original PDF code errors:** Lab 8/9 samples contain syntax/register/mask
   errors. Built-in examples are corrected references, not verbatim PDF source.
   See [BOARD_NOTES](BOARD_NOTES.md) for the established corrections.
7. **Exercise limits:** all 18 references compile and boot. Connectivity tests
   do not prove complete counter rollovers, every direction sequence or arbitrary
   student firmware. Partial-verification labels in
   [LAB_COVERAGE](LAB_COVERAGE.md) still apply.

## Reproduction and verification

Added [38 backend audit tests](../tests/test_manual_connectivity.py) and
[3 browser peripheral tests](../browser-tests/peripherals.spec.ts).

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=build/peripheral-audit-results.xml
npm.cmd run build
# Separate terminal: isolated server
$env:LPC_LAB_PORT='8876'
.\.venv\Scripts\python.exe -m simulator.server
# Browser-test terminal
$env:LPC_LAB_URL='http://127.0.0.1:8876'
npm.cmd run test:browser -- --output=test-results/peripheral-audit-browser
```

Final verification on 29 October 2026:

* Backend: **93 passed**, zero failures, 109.17 seconds. JUnit evidence:
  `build/peripheral-audit-results.xml`.
* Browser: **26 passed**, zero failures, 47.5 seconds, against port 8876.
* Frontend: `npm.cmd run build` passed (TypeScript and Vite).

Screenshots: `test-results/peripheral-keypad-lcd.png`,
`test-results/peripheral-adc-lcd.png`, `test-results/peripheral-seven-segment.png`,
`test-results/peripheral-pwm.png`. Files under `build/` and `test-results/` are
generated artifacts ignored by version control.
