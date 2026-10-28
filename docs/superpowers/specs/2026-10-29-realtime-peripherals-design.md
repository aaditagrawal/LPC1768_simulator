# Real-time peripheral timing

User intent: timer-driven student firmware should visibly run at its configured
rate. The frontend polling interval must remain unchanged. The user's request to
just make it work authorizes implementation without another design questionnaire.

Use a monotonic elapsed-time clock for Timer0–3 and PWM in the live Runtime.
Derive CCLK from the oscillator/PLL0/CCLK divider registers and peripheral clocks
from PCLKSEL0/1. Preserve integer fractions and prescaler state; account time before
clock/power/timer configuration changes. Pause freezes time; resume reanchors the
host clock; loading/resetting establishes a fresh epoch.

Execute real firmware in bounded, short worker slices without the unconditional
2 ms sleep that prevents servicing a 1 ms polling loop. This is a CPU scheduling
change, not a presentation polling change. Keep offline instruction-driven mode
for deterministic existing integration tests, and inject a monotonic clock for
precise real-time unit tests.

Seven-segment reconstruction uses a fixed physical persistence interval in live
mode instead of an instruction-count window. GPIO writes still determine display
contents; snapshots never invent counter values or execute source-specific logic.

Alternatives considered: pacing every CPU instruction to full MCU speed is not
feasible with the Python MMIO model; changing UI polling does not fix clocks and
is expressly excluded. Wall-clock peripheral timing is the chosen approach.

Limits: CPU throughput, software delay loops, high-rate IRQ service and exact
waveforms remain host-dependent. ADC conversion latency and unsupported hardware
are outside this change. Invalid firmware such as reset-only MCR remains invalid.

Acceptance: compiled timer polls/IRQs follow elapsed time and PCLK settings;
pause/resume does not catch up paused time; the user's corrected seven-segment
program multiplexes and advances about once per second with responsive SW2;
existing firmware/routing/browser tests pass; web polling is untouched.
