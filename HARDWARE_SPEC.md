# Hardware-fidelity specification

Audit date: 2026-10-29. This specification separates documented hardware from the
implemented subset. A passing software test is evidence for its stated scope; it
is not a physical-board measurement. Final execution totals belong in
`TEST_REPORT.md`. Final results are recorded after running the complete regression suite.

## Evidence and precedence

1. Physical observations and measurements: **none supplied**. Board photographs
   establish component placement, not electrical continuity or timing.
2. ALS board manual for external connections and components.
3. NXP LPC17xx register semantics and installed CMSIS device definitions.
4. ESD lab manual for exercise intent and sample programs.
5. Explicit engineering assumptions where these sources leave a question open.

All page references below are **one-based PDF pages**, followed by printed pages
where useful. Both local PDFs were read in full, including inspection of the
image-only keypad, display, LCD command and connector diagrams. Extracted text
and inspected diagram images are in `build/hardware-audit/`.

| Supplied local file | Pages | SHA-256 |
|---|---:|---|
| `ESD.pdf` | 65 | `9b93d75fc0c1815ac02127ddb522d52c3b643c7fa298ecb8d5f07a095eebf97b` |
| `ARM_LPC-1768_User_Manual (1).pdf` | 61 | `06e5bec536f259b1d409a0768e22478553c03bf0feb3b7d8ffdc9f7dd49c7bb7` |

The request calls these `ESD(1).pdf` and
`ARM_LPC-1768_User_Manual (1)(2).pdf`. Those filename variants are not present;
the hashes identify exactly which available editions were audited. The board
document is ALS-SDA-ARMCTXM3-01-UM1, with a 2014 cover. The ESD cover says
ICT3143, semester V CCE, July–November 2025. Its contents page uses pagination
that differs from the supplied PDF; use the PDF references in this report.

Register layouts were cross-checked with the installed NXP CMSIS header
`C:/Keil/ARM/INC/NXP/LPC17xx/LPC17xx.h`. Board manual PDF p15 explicitly refers
to NXP UM10360 for MCU details. For example, the prescaler equality rule is in
[NXP UM10360, Timer chapter](https://www.pololu.com/file/0J431/user.manual.lpc17xx.pdf),
an NXP-authored manual hosted by a distributor. The ALS bibliography's
`UM10306.pdf` spelling on p61 is not used as a different register oracle.

## Execution mechanism and boundaries

`simulator/compiler.py` invokes the installed Keil ARMCC/ARMASM/ARMLINK/FROMELF
toolchain for Cortex-M3 Thumb code, C99 and microlib. The UI defaults to `-O0`;
Python callers can select `-O0` through `-O3`, all tested. It links the installed
NXP startup and `system_LPC17xx.c`, then loads Intel HEX. Source text is not
interpreted by the simulator. Uploaded HEX takes the same execution path.

`simulator/engine.py` runs the resulting Thumb/Thumb-2 instructions in Unicorn
2.1.4 M-class mode. Python callbacks implement MMIO, physical connections and
device state. GPIO transitions drive the display models. There is no observed
source-name matching, variable-name delay recognition, calculator answer
injection, or exercise-specific output logic in the runtime/engine. The catalog
selects files and supplies a wiring checklist; it does not patch loaded firmware.

Flash is mapped at `0x00000000–0x0007FFFF`; CPU SRAM at
`0x10000000–0x10007FFF`; the two AHB SRAM banks are mapped together at
`0x2007C000–0x20083FFF`. Intel HEX is validated against those ranges, initial SP
alignment and SRAM location, a Thumb reset vector in loaded flash, and EOF.
Flash programming/IAP, flash access latency, MPU protection and bit-band aliases
are not modeled. Unicorn RAM initially contains zeros; this is not a promise
about uninitialized physical SRAM after reset.

Live Runtime advances supported peripherals from active monotonic elapsed time.
Pause accounts the final interval and freezes it; resume reanchors; reset/load
make a new MCU epoch while retaining physical connections, inputs and pots.
Offline `Machine()` defaults to instruction-derived deterministic timing.
Instruction ticks count basic-block halfwords, not true Cortex-M3 clock cycles.
Busy loops execute real code but their wall time remains host-dependent.
The frontend's existing 150 ms state polling interval is unchanged.

## Every modeled FRC connector

Connections are ten-conductor, pin-to-same-pin ribbons. Each header accepts one
cable. Any supported pair can be connected; matching names never auto-connect.
`NC` below means no modeled conductor node. Pin numbering is electrical numbering,
not the drawing's visual order. All ten connectors below have pin10 = ground.

| Header | Pins1–8, in order | Pin9 | Source |
|---|---|---|---|
| CNA | P0.4, P0.5, P0.6, P0.7, P0.8, P0.9, P0.10, P0.11 | NC | Board p24; ESD p63 |
| CNB | P1.23, P1.24, P1.25, P1.26, P2.10, P2.11, P2.12, P2.13 via JP4 | NC | Board p25; ESD p64 |
| CNC | P0.15, P0.16, P0.17, P0.18, P0.19, P0.20, P0.21, P0.22 | P2.13 via JP4 | Board p25; ESD p64 |
| CND | P0.23, P0.24, P0.25, P0.26 via JP5, P0.27, P0.28, P2.0, P2.1 | NC | Board p26; ESD p65 |
| CNA1 | LD2, LD3, LD4, LD5, LD6, LD7, LD8, LD9 anodes | NC | Board pp34–35 |
| CNA2 | a, b, c, d, e, f, g, decimal-point segment data | NC | ESD p31 schematic; board p37 |
| CNB2 | U7 address A, B, C, D, NC, NC, NC, NC | NC | Board p37; ESD p31 schematic |
| CNB3 | COL1, COL2, COL3, COL4, ROW1, ROW2, ROW3, ROW4 | NC | ESD p42 schematic; board p36 |
| CNAD | LCD D4, D5, D6, D7, RS, E, NC, NC | NC | Board pp31–32; ESD p37 |
| CNB1 | LD10/PWM, NC, **unmodeled match**, **unmodeled capture**, NC, NC, SW2 in lab profile, NC | SW2 in alternative profile | Board pp36–37, ambiguous SW2 table; ESD p29 |

For CNA2, the actual external buffer U12 is a 74HCT244 and U7 is a 74LS145
BCD-to-decimal decoder in the ESD p31 schematic. The simulator models their
logical selection/data effect, not propagation delay, current limits or voltage
thresholds. Codes0–3 select U8–U11; other address codes enable none of these four
displays. Segments are active-high common-cathode, bit0=a through bit7=dp.
The schematic has 10 kΩ pulls on decoder address inputs; floating lines cannot
be treated as four independent permanent digit enables.

Every GPIO-header pin's alternate-function label can be found in the cited
connector tables. Only the GPIO, AD0.4/5, PWM1.4 on P1.23 and EINT0–3 on
P2.10–13 paths are currently useful in this simulator. For example, selecting
P0.6/MAT2.0 cannot produce an external-match waveform just because PINSEL stores
that selection. P0.27/28 are shared with I²C0/USB OTG; those interfaces are absent.

### SW2 ambiguity: unresolved physical wiring

ESD PDF p29 (printed25) expressly says CNB1 pin7. With CNB→CNB1 this reaches
P2.12/EINT2 and matches Lab6's P2.12 requirement. The ALS table on PDF p37
(printed36) says pin9 is both NC and external interrupt, omits pin7, and directs
CNB→CNB1 even though CNB pin9 is NC. These statements cannot all describe one
straight-through cable. The default is the documented **lab pin7 profile**,
released high and pressed low. A separate pin9 profile preserves the alternative
statement; it does not secretly route CNB pin9 to P2.12. Physical continuity
measurement is needed to settle this. EINT2 tests validate the selected profile,
not a measured trace on the actual board.

## Jumpers and physical dependencies

| Jumper | Documented action | Implemented scope |
|---|---|---|
| JP4, three pins | 1–2 routes P2.13 to CNB.8; 2–3 routes it to CNC.9; open isolates both | Actual connection gating |
| JP5, two pins | Closed routes P0.26 to CND.4; open allows DAC use at TP8 | Actual CND.4 gating; DAC absent |
| JP16, two pins | Short to use text LCD; text and graphic LCD mutually exclusive | Text LCD enable gating; graphic LCD absent |
| JP18, three pins | 2–3 routes POT4 to AD0.4; 1–2 selects USB device function | Actual AD0.4 gating; USB absent |

Sources: board pp25–26,30–34,50–51; ESD pp41,44–45. All four modeled jumpers
start open. Reset preserves them, as a physical MCU reset would.

Other visible selectors JP7/8 (UART3/CAN1), JP12/13 (RS485/SPI), and JP17
(graphic LCD) only retain browser-side shunt positions. They have **no electrical
effect**. The remaining board references include JP1 (+5 V NIFC), JP2 (RTCK),
JP3 (ISP), JP6 (3.3 V board supply), JP9 (CAN test), JP10/11 (RS485), JP14
(capture/match loopback), JP15 (external RTC interrupt), JP19 (USB host/CLKOUT).
These are unmodeled, not silently included in the four active jumper semantics.

Other physical connectors CN1–4 (piggyback), CN5/7 (debug/trace), CN6 (26-pin
NIFC), CN8 (power), CN9/RM1 (UART), CN10/CND1 (graphic LCD), CN11 (physical
text-LCD socket), CN12/CNA5/RM5/PM1 (relay/motors), CN13 (Ethernet), CN14/15/18
(USB), CN16 (spare pins), CN17/CNA4 (I²S), CNC1 (SPI/I²C/RS485), RM2 (CAN),
RM3 (RS485) and RM4 (capture input) are not user-wireable electrical nodes.
CN11's text interface is represented through CNAD; it is not a detachable module.
Testpoints TP1–TP9 are artwork, not measurement instruments.

## Register inventory and required semantics

An accepted address is not necessarily a fully implemented peripheral. Reads and
writes outside dispatch-supported addresses raise `FirmwareError`; accepted
register storage must not be confused with tested hardware semantics.

### GPIO / pin connect

For ports0–4, base `0x2009C000 + 0x20*port`, the accepted word offsets are:

| Offset | Register | Observable behavior |
|---:|---|---|
| 0x00 | FIODIR | 1=output, 0=input; mux must select GPIO to drive |
| 0x10 | FIOMASK | Masked FIOPIN access must preserve/exclude masked bits |
| 0x14 | FIOPIN | Read actual logical pin state; write replaces unmasked output latch bits |
| 0x18 | FIOSET | Writing1 sets selected latch bits; zero leaves others alone |
| 0x1C | FIOCLR | Writing1 clears selected latch bits; zero leaves others alone; reads not a signal oracle |

Byte/halfword aliases use the same aligned-word MMIO callback and access mask.
Latches can change while a pin is input; the input must not drive the external
load until FIODIR/mux permits it. Input pulls use PINMODE0–9 at
`0x4002C040–0x4002C064`, two bits per pin. GPIO mux uses PINSEL0–9 at
`0x4002C000–0x4002C024`. PINSEL10 is at +0x28. The entire aligned range
`0x4002C000–0x4002C07C` is accepted, including reserved gaps, PINMODE_OD0–4
(+0x68–0x78) and I2CPADCFG (+0x7C); accepting these addresses does not by itself
model debug selection or I²C electrical behavior. PINMODE_OD0–4 implement
open-drain release for GPIO and the PWM pad, tested separately. Repeater mode,
all reset-function exceptions, package-unavailable pins and analog electrical
levels require separate evidence; see the gaps report.

### System control, clocks and external interrupts

System-control base is `0x400FC000`. Accepted offsets at audit start:

| Offsets | Registers / interpretation |
|---|---|
| 0x000 | FLASHCFG; storage, no flash wait-state timing |
| 0x080/084/088/08C | PLL0CON/CFG/STAT/FEED |
| 0x0A0/0A4/0A8/0AC | PLL1CON/CFG/STAT/FEED; USB absent |
| 0x0C0/0C4 | PCON / PCONP; no true CPU sleep/power-down |
| 0x104/108/10C | CCLKCFG / USBCLKCFG / CLKSRCSEL |
| 0x110/118 | CAN-related/reserved storage; CAN not implemented |
| 0x140/148/14C | EXTINT / EXTMODE / EXTPOLAR |
| 0x180/184/188 | RSID and adjacent accepted storage; physical reset causes absent |
| 0x1A0/1A8/1AC | SCS / PCLKSEL0 / PCLKSEL1 |
| 0x1B0/1B8 | Accepted reserved storage; no peripheral effect |
| 0x1C0/1C4/1C8 | USBIntSt / DMAREQSEL / CLKOUTCFG; corresponding interfaces absent |

Clock source choices are IRC4 MHz, main oscillator12 MHz, RTC32768 Hz. CCLK
derives from PLL0 multiplier/predivider and CCLKCFG+1 when connected, or selected
oscillator divided by CCLKCFG+1 when bypassed. Timer/PWM PCLK selections map
0/1/2/3 to CCLK/4,/1,/2,/8. Time before a mutation is charged at the old rate.
PLL feed sequencing, analog lock time, oscillator stabilization and invalid clock
range enforcement are not complete hardware models: status is synthesized for
startup compatibility. Board pp46–47 recommends a **different setup** (PLL off,
12 MHz/4=3 MHz, peripherals at CCLK), whereas the installed default startup used
here configures100 MHz. The compiled startup controls the actual model; do not
transfer raw busy-loop timing between those setups.

PCONP bit15 (PCGPIO) controls IOCON/GPIO/GPIO interrupts in NXP Table46.
The model's GPIO/PINCON accesses do not enforce this gate; this is an explicit
unsupported power-control path, distinct from the tested timer/PWM/ADC gates.
Clearing PCGPIO can therefore give false-positive GPIO results in this simulator.

EXTINT is write-one-to-clear. EINT0–3 require P2.10–13 function1. EXTMODE chooses
edge/level and EXTPOLAR rising/high or falling/low. The connected SW2 supplies
logical transitions. General GPIO edge-interrupt controller registers are not
implemented. Mechanical bounce is not automatically added.

### Timer0–3

| Timer | Base | PCONP bit | PCLKSEL register/bits | IRQ |
|---|---|---:|---|---:|
| 0 | 0x40004000 | 1 | PCLKSEL0[3:2] | 1 |
| 1 | 0x40008000 | 2 | PCLKSEL0[5:4] | 2 |
| 2 | 0x40090000 | 22 | PCLKSEL1[13:12] | 3 |
| 3 | 0x40094000 | 23 | PCLKSEL1[15:14] | 4 |

Offsets0x00–0x24 implement IR,TCR,TC,PR,PC,MCR,MR0–3. TCR bit0 enables; bit1
holds reset. PC reaches PR then resets and increments the32-bit TC on the next
PCLK. Lowering PR below PC waits for PC wrap and equality. MCR's three bits per
match independently request interrupt/reset/stop. IR latches interrupt-enabled
matches and is write-one-to-clear; multiple elapsed matches do not queue millions
of IRQ deliveries. Power gating and pause stop counting. Reset/load remove
fractional residual time. Match batching must remain bounded after a host stall.

Offsets0x28–0x3C (CCR,CR0/1,reserved,EMR) and0x70 (CTCR) have historically been
accepted storage. External counter/capture inputs, EMR waveforms and DMA requests
are outside implemented scope unless explicitly rejected or added in this audit.

### PWM1

Base `0x40018000`, PCONP6, PCLKSEL0[13:12], IRQ9. Common timer offsets0x00–0x3C,
MR4/5/6 at0x40/44/48, PCR0x4C, LER0x50 and CTCR0x70 are accepted. Lab output
is P1.23 function2 = PWM1.4 → CNB.1 → CNB1.1 → LD10. Required gates include
power, correct pin mux, TCR counter/PWM enables and PCR PWMENA4. MR0 determines
period and MR4 single-edge high duration. PWM TC holds values1 throughMR0 and
resets to1; elapsed phase is represented separately from this register value.
MR4–6 interrupt flags use IR bits8–10. LER schedules shadow updates at period
boundaries; a written MR value must not affect the active duty before latching.
The audit specifically tests this requirement, actual level/frequency behavior,
stop/reset controls, invalid matches and all requested duty levels. See final
verification results for the implementation added during this audit.

PWM1.1–3/5–6 board outputs, double-edge mode, external counting and DMA are not
established by the LD10 single-edge tests. LD10 rendering is average logical duty,
not a calibrated luminous-intensity or analog TP6 model.

### ADC

Base `0x40034000`; ADCR0x00, ADGDR0x04, ADINTEN0x0C, ADDR0–7 at0x10–0x2C,
ADSTAT0x30, ADTRM0x34. Only AD0.4/P1.30 function3 and AD0.5/P1.31 function3
have modeled board analog inputs. AD0.4 needs JP18=2–3; AD0.5 is POT1 direct.
PCONP12 and ADCR.PDN must be enabled. Channel selection, CLKDIV, START, BURST,
DONE, overrun, read side effects, conversion latency and interrupts require the
NXP ADC oracle, not the lab sample's incorrect DONE expression. The ADC audit
tests all4096 ideal code centers and threshold boundaries; final status is in
`TEST_REPORT.md`. Analog tolerance/noise and physical disconnected-input voltage
remain unverified. Unsupported channel selections must not produce invented POT
values. ADTRM storage does not establish factory trim/calibration behavior.

### Core control and interrupt subset

NVIC ISER0/ICER0 at `0xE000E100/180`, ISPR0/ICPR0 at `0xE000E200/280`, and
IABR0 at `0xE000E300` implement a flat interrupt subset. Lowest IRQ number wins,
PRIMASK gates entry, and software stacks/restores a basic exception frame.
No nested preemption, priority arbitration, tail-chaining or late-arrival timing
is modeled. Priority bytes `0xE000E400–420` are stored but do not set scheduling
priority. The second NVIC bank and IRQ32+ are not generally implemented.

CPUID at `0xE000ED00` is a fixed Cortex-M3 identity. ICSR/VTOR/AIRCR/SCR/CCR at
ED04/08/0C/10/14 are accepted storage; VTOR affects vector lookup. AIRCR reset,
SysTick, PendSV/SVC, fault escalation, BASEPRI/FAULTMASK/MSP/PSP interactions and
debug behavior are not complete Cortex-M3 models. An unsupported CPU exception
raises a firmware error instead of faithfully entering its hardware handler.

## External devices

LEDs LD2–LD9 are active high; the model resolves actual routed logical pin levels.
Disconnecting their ribbon removes drive. Electrical loading, resistor current
and persistence at very high blink rates are not modeled.

The text LCD uses CNAD.1–4=D4–7, .5=RS, .6=E and JP16. CND→CNAD additionally
requires JP5 for D7. Transactions occur on E falling edges, in command/data mode,
with high nibble then low nibble. DDRAM, addressing and display-enable state
determine16×2 text. The lab p38 command chart specifies37 µs typical instructions
and1.52 ms clear/home; timing compliance is not guaranteed by the logical parser.
POT3 contrast, CGRAM glyph shapes, blink/cursor and analog bus thresholds are
separate limitations, even when printable text tests pass.

The keypad is physical SW3–SW18 arranged row-major4×4. Code `row*4+column` maps
to displayed labels0–F; this is a UI/reference convention, not ASCII injected
into firmware. ESD p42 schematic explicitly shows15 kΩ column pulldowns and
**D6–D9 1N5819 row-isolation diodes**. A correct logical network must respect
their direction and still permit physically justified multi-key ghost paths.
Key hold/release and polling are controlled by firmware. Automatic single-shot
keypress delivery and automatic debouncing are not hardware behavior.

Seven-segment reconstruction is a rendering approximation: valid selected digits
and actual segment masks accumulate over a50 ms active-time history in live mode;
instruction dwell suppresses brief software blanking. It is not a photometric
brightness/flicker/ghosting model. Offline history uses instruction ticks.

## Integration constraints and known manual discrepancies

* CNB cannot simultaneously carry independent CNB2 and CNB3/CNB1 ribbons. The
  alternate-header paths in example metadata are substantive wiring choices.
* With CNA→CNA2 and CNB→CNB2, CNC→CNB1 puts the lab SW2 profile on P0.21.
  Firmware must read P0.21; it cannot continue reading P2.12 as if CNB were free.
* PWM1.4 consumes P1.23/CNB.1; keyboard+PWM requires another GPIO header for
  CNB3. The standalone keyboard-PWM example uses CND and JP5 for column4.
* LCD data on P0.23–26 conflicts with using the same CND pins for a separate
  keypad ribbon; the model does not add a splitter or flying leads automatically.
* ESD Lab7 sample pp28–29 contains missing semicolons/prose as C; corrected
  files are separate sources. Lab8 pp32–35 mixes `Delay/delay`, `Display/display`
  and invalid `Void/For`; its software loop is not an independently calibrated
  one-second timer.
* ESD keypad pp42–44 configures P2 pins through PINSEL3 instead of PINSEL4,
  reads GPIO0 instead of GPIO1, uses incorrect masks, malformed scopes and an
  unimplemented Display function. A faithful simulator must not repair those
  register mistakes while executing the original program.
* ESD ADC p46's DONE loop compares the entire ADGDR word to0x80000000 instead
  of testing bit31; its divider also needs adjustment with this repository's 100 MHz startup.
  The manual's separate 3 MHz clock profile can use CLKDIV=0. Corrected examples
  set a safe divider and disable analog-pin pulls explicitly.
* ESD PWM p49 labels MR4 as MR1 in a comment; PWM1.4 uses MR4. The dice reference
  now follows the explicit 0–6 prose and uses the required external interrupt.
  Its interrupt-sampled loop phase is deterministic, not calibrated randomness.
