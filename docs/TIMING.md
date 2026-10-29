# Timing behavior

Live Timer0–Timer3 and PWM1 counters now advance from a monotonic host clock.
They no longer use executed instruction counts as their time source. The browser
continues polling at its existing 150 ms interval; it is only a presentation layer.

The configured oscillator (4 MHz IRC, board 12 MHz crystal or 32.768 kHz RTC
source), PLL0 multiplier/predivider, CCLK divider and each peripheral's PCLKSEL
field determine clock rate. PR/PC prescaling retains fractional clock progress.
Register changes account for the preceding interval before applying new settings.
Pausing freezes active time; resuming establishes a new host-time anchor. Reset
and firmware loading start a fresh clock while retaining physical configuration.

Timer flag behavior is unchanged: MR0I must be set to produce IR bit 0; MR0R
alone only resets TC. Flags latch, so firmware that services a timer too slowly
can miss periods just as a slow CPU can miss repeated status events. Whole reset
periods are batched after a host stall to keep execution bounded, including when
a later stop match is unreachable behind an earlier reset.

The worker executes bounded 1 ms slices and yields to input/API threads without
an unconditional 2 ms sleep. This permits firmware polling a 1 ms timer to run
near its intended cadence. It does not change any browser interval.

Seven-segment history expires after 50 ms of active time. Its relative dwell
weights still use executed instruction ticks, so Python's MMIO overhead does not
turn a few blanking instructions into a dominant blank pattern. Every displayed
pattern still comes from actual GPIO writes. Pause freezes persistence too.

## Verification

`tests/test_realtime.py` checks PCLK selection for all four timers, oscillator and
PLL-derived clocks, fractional progress, dynamic prescaler changes and wrap,
power/mux changes, match flags/IRQ execution, timer stop/reset, PWM, large host
gaps, pause/resume/reset and multiplex persistence.

`tests/fixtures/realtime_counter.c` is the user's counter with MCR corrected from
0x02 to 0x03. The wall-clock integration test compiles it and observes 0001,
0002 and 0003 at approximately one-second intervals. The browser test also
checks actual rendered digits, a paused interval longer than one second and
SW2 reversing the direction.

Use CNA→CNA2, CNB→CNB2 and CND→CNB1 for that firmware: its switch input is
P2.0, not the built-in example's alternative P0.21 route.

For the first measured local run, 0001/0002/0003 were observed at 1.043,
2.080 and 3.098 seconds. Results depend on host load; they do not promise hard
real-time scheduling or cycle accuracy.

Final regression run: 117 backend tests and 27 browser tests passed; the standard
TypeScript/Vite build passed. The updated main service on port 8765 was restarted
and its rendered counter was checked again. Live service evidence is saved in
`build/realtime-live-verification.json`; screenshots are in
`test-results/realtime-live-board.png` and `realtime-live-seven-segment.png`.
The browser polling source is byte-for-byte identical to its pre-change backup.

## LCD and keypad response

A `for(... < 50000)` delay still executes all of those CPU instructions. Faster
browser updates cannot make that firmware finish sooner. The standalone
[timer-based calculator](../examples/calculator_timer.c) replaces those waits with
Timer0 delays and uses the manual keypad direction: P2.10–13 drive rows and
P1.23–26 read columns. It preserves the user's alternate key map: A adds, B
subtracts, F equals and E restarts. This differs from the built-in Lab 9 reference,
where E equals and F clears.

The calculator browser check measured its full prompt at about 364 ms and the
largest backend-to-render delay at about 160 ms with the unchanged 150 ms UI
interval. The test also verifies 3+4=7, 2−8=−6 and 9+9=18 through actual keypad
controls; backend checks include −9/zero results and release behavior. Evidence:
`test-results/calculator-render-latency.json`, `tests/test_user_calculator.py` and
`browser-tests/calculator.spec.ts`.

## Limits

CPU instructions, software delay loops and high-frequency interrupt handlers
remain limited by Unicorn/Python/host throughput. ADC conversion now takes 65
configured ADC clocks; PWM1.4 has counter-derived electrical levels and defers
updates to a cycle boundary. PLL lock/feed sequencing, clock tolerance and
unsupported peripherals remain limitations. See the root hardware audit reports. Invalid timer configuration remains
invalid. The direct `Machine` default uses deterministic instruction-derived
timing for offline tests; `Runtime` with its live worker enables elapsed time.

Clock register references: NXP UM10360 sections 4.4–4.7 and 21.6,
[LPC17xx user manual](https://www.pololu.com/file/0J431/user.manual.lpc17xx.pdf).
