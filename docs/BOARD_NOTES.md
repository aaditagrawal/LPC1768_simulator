# Mapping evidence and lab corrections

Page numbers below are PDF page indices counted from 1, not printed footer numbers.

* Board manual pp.24–26: CNA.1–8 = P0.4–11, CNB.1–4 = P1.23–26,
  CNB.5–8 = P2.10–13; CNC.1–8 = P0.15–22, CNC.9 = P2.13;
  CND.1–6 = P0.23–28, CND.7–8 = P2.0–1. Pin 10 is ground, pin 9 NC
  except CNC. JP4 chooses CNB.8 (1–2) or CNC.9 (2–3), JP5 enables CND.4.
* pp.31–32: CNAD.1–4 = LCD D4–D7, .5 = RS, .6 = Enable, JP16 required.
  The table repeats L5 for RS/Enable; use pin numbers and the lab's GPIO map.
* pp.33–34: POT1 = P1.31 / AD0.5; POT4 = P1.30 / AD0.4 with JP18 2–3.
  POT5 occurs in unrelated Ethernet demo instructions (p.58), without a verified
  ADC route. POT5 is deliberately omitted, and is not treated as POT1.
* pp.34–35: CNA1.1–8 drive LD2–LD9, active high. Other MCU headers may also
  drive the LED bank through the same pin-to-pin ribbon wiring.
* pp.36–37: keypad rows drive high and columns have external pulldowns.
  The prose does not list every keypad pin, but ESD Lab 9 (pp.42–44) and CNB's
  table establish columns on CNB3.1–4, rows on .5–8. This is an inferred map,
  with its evidence stated, rather than an independently checked schematic.
* pp.36–37: CNB1.1 drives LD10 / PWM1.4. The SW2 table lists pin **9** as both
  NC and external interrupt; it omits pin 7. CNB.9 is NC, so a straight CNB
  cable could not produce an interrupt on that route. ESD Lab 7 (p.29) says
  CNB1 pin **7**, giving P2.12/EINT2 and agreeing with the requested lab.
  Default profile: SW2 on pin 7, active low, pulled high when released. The UI
  offers pin 9 as a documented alternative; on CNB it intentionally does not
  magically connect to P2.12. A photograph alone cannot establish the trace.
* p.37: U7 receives a **BCD address**, not four independent one-hot digit
  enables. CNB2.1–4 = A,B,C,D; values 0–3 select the four digits. Value 5 in
  the sample disables all four. CNA2 carries a,b,c,d,e,f,g,dp, active high.
* ESD Appendix C, pp.63–65, agrees with the MCU-header map above.

## Jumper geometry audit

The supplied board manual and uncabled photograph are the evidence for physical
geometry. A list of software states does not establish the number of pins.

| Jumper | Pins drawn | Evidence and implemented scope |
|---|---|---|
| JP4 | 3 | Manual p.25 explicitly selects 1–2 for CNB.8 or 2–3 for CNC.9; both routes are modeled. |
| JP5 | 2 | Manual p.26 specifies short/open gating of CND.4; the photograph corroborates the two-pin header. |
| JP16 | 2 | Manual p.31 specifies shorting for the text LCD; the photograph corroborates the two-pin header. |
| JP18 | 3 | Manual p.30 selects 1–2 for USB device, pp.34 and 51 select 2–3 for ADC0.4. Page 51 places it in the USB device block. Only the ADC route is emulated. |
| JP7, JP8 | 3 | Manual pp.29 and 50 select 1–2 for UART3, p.34 selects 2–3 for CAN1. Movable shunts in the CAN block; associated interfaces unmodeled. |
| JP12, JP13 | 3 | Manual p.35 selects 1–2 for RS485 or 2–3 for SPI. Movable shunts above the SPI block; associated interfaces unmodeled. |
| JP17 | 3 | Manual p.50 explicitly selects 2–3 for the graphic LCD. Movable shunt beside the graphic LCD connector; graphic LCD unmodeled. |

Two-pin headers expose two gold pins when open and one shunt over the pair when
closed. Three-pin headers expose all three pins when open; a selected shunt
covers exactly 1–2 or 2–3. All jumpers start open. The five selectors for
unmodeled interfaces accept clicks and Enter/Space; their physical positions
are saved in browser storage, without backend routing or electrical effects.
Other short/open references
do not establish a physical pin count, so this audit does not infer additional
three-pin selectors from them. Positions and orientation are approximate.

Active jumper geometry falls back to the bundled manual-backed mapping if an
already-running service omits pinCount metadata. A frontend rebuild can thus
restore visible, clickable headers without restarting the firmware session.

Identifiable artwork labels follow the manual: UART CN9 and SW21 (p.28), power
CN8 (p.20 and photograph), graphic LCD CND1 (p.32), USB device SW20 (p.30).
The seven-segment chips are labeled U12 buffer and U7 BCD decoder (p.37),
without asserting an unverified part number.

## Corrected reference programs

Original PDFs remain untouched. `examples/` contains separate corrected,
self-contained C programs; helpers issue actual register writes/reads.

* Lab 7: missing semicolons and prose presented as C are corrected; delay
  counters are volatile so compiler optimization cannot remove them.
* Lab 8: hexadecimal segment code `0x7D` for 6 is retained. Digit selection is
  decoded from P1.23–26 as BCD. Delays are bounded; logical timing is approximate.
* Lab 9 keypad: the second PINSEL3 access for P2.10–13 should be **PINSEL4**.
  `scan()` incorrectly reads GPIO0 instead of **GPIO1**, uses masks shifted
  four bits too low, has malformed scope and lacks `Display(key)`. Corrected
  examples read `(GPIO1->FIOPIN >> 23) & 15` and implement the missing display.
  SW3–SW18 labels use row-major 0–F keycodes; row/column mapping is explicit.
* LCD initialization uses single-nibble 3,3,3,2 followed by byte commands
  0x28/0x0C/0x06/0x01, as required by the lab's four-bit protocol.
* Lab 10: enable ADC peripheral power, choose channel 5 in ADCR and configure
  PINSEL3 bits 30–31 for P1.31. The channel-4 example separately sets bits
  28–29 and requires JP18 2–3. Floating-point `sprintf` is avoided in reference
  examples for small code size; user C still links Keil microlib normally.
* Lab 11: MR4 (not the MR1 comment) controls PWM1.4. The example configures
  PINSEL3 bits 14–15 to function 2, PCR bit 12, MR0/MR4, LER and TCR.

Coordinates in `board/layout.json` refer to the 1440 × 1040 top-down SVG board.
`web/BoardArtwork.tsx` reconstructs the physical arrangement from the clearer,
uncabled supplied JPEG. Its passive component details and traces are visual
approximations, not a fabrication drawing or independently verified schematic.
The orientation metadata rotates CNB, CNC, CNB1 and CNAD to match the photo.
Electrical routing still comes from the manual and `board/mapping.json`,
independently of drawing coordinates. The original photographs are retained.
