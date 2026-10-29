"""Independent integer-clock oracles: NXP UM10360 ch24 tables446/449/452.

One microsecond is one PWM clock in these reset-clock register probes.
No expected waveform is obtained from the model's duty calculation.
"""
from pathlib import Path
import random

import pytest

from simulator.engine import Machine
from simulator.compiler import Compiler
from fidelity_vector_support import vector_log


class Clock:
    ns = 0

    def __call__(self):
        return self.ns


def setup(duty=250, period=1000):
    clock = Clock()
    m = Machine(Path('examples/idle.hex').read_text(), realtime=True, clock_ns=clock)
    m.write_word(m.SC + 0xC4, m.regs[m.SC + 0xC4] | 64)
    m.write_word(m.PIN + 12, 2 << 14)
    for off, value in [(4, 2), (12, 0), (24, period), (64, duty),
                       (20, 2), (76, 1 << 12), (80, 17), (4, 9)]:
        m.write_word(m.PWM + off, value)
    m.board.connect('CNB', 'CNB1')
    m.resume_clock()
    return m, clock


def advance(m, clock, us):
    clock.ns += us * 1000
    return m.read_word(m.PWM + 8)


@pytest.mark.parametrize('percent', [0, 1, 10, 25, 50, 75, 90, 99, 100])
def test_pwm_measured_pin_high_low_and_frequency(percent, vector_log):
    m, clock = setup(percent * 10)
    levels = []
    for _ in range(2000):
        advance(m, clock, 1)
        levels.append(m.pin_output(1, 23))
    assert set(levels) <= {0, 1}
    assert sum(levels) == percent * 20
    assert levels[:1000] == levels[1000:]
    assert m.snapshot()['pwm'] == pytest.approx(percent / 100)
    rising = [i for i in range(1, len(levels)) if levels[i - 1] == 0 and levels[i] == 1]
    frequency = 1_000_000 / (rising[-1] - rising[-2]) if len(rising) > 1 else None
    expected = {'high_us': percent * 20, 'low_us': 2000 - percent * 20,
                'frequency_hz': 1000.0 if 0 < percent < 100 else None}
    observed = {'high_us': sum(levels), 'low_us': 2000 - sum(levels),
                'frequency_hz': frequency}
    vector_log(m, f'duty-{percent}', expected, observed,
               {'sample_interval_ns': 1000, 'samples': 2000, 'MR0': 1000, 'MR4': percent * 10},
               11, 'UM10360 24.4.1, tables447/449/452; constant outputs have no measurable edge frequency')
    assert observed == expected


def test_pwm_ler_waits_for_cycle_boundary_and_retains_pending_bits():
    m, clock = setup()
    advance(m, clock, 400)
    m.write_word(m.PWM + 64, 750)
    m.write_word(m.PWM + 80, 16)
    assert m.read_word(m.PWM + 80) & 16
    assert m.pwm_duty() == .25
    assert m.pin_output(1, 23) == 0
    advance(m, clock, 599)
    assert m.pwm_duty() == .25
    advance(m, clock, 1)
    assert m.read_word(m.PWM + 80) == 0
    assert m.pwm_duty() == .75
    assert m.pin_output(1, 23) == 1


def test_pwm_unlatched_period_write_does_not_change_counter_reset():
    m, clock = setup()
    advance(m, clock, 1100)  # consume initialization's pending LER first
    m.write_word(m.PWM + 24, 2000)
    assert advance(m, clock, 900) == 1
    assert m.pwm_duty() == .25


def test_pwm_match4_interrupt_uses_ir_bit8_and_write_one_clear():
    m, clock = setup()
    m.write_word(m.PWM + 20, 2 | (1 << 12))
    advance(m, clock, 249)
    assert m.read_word(m.PWM) == 0
    advance(m, clock, 1)
    assert m.read_word(m.PWM) == 1 << 8
    m.write_word(m.PWM, 1 << 8)
    assert m.read_word(m.PWM) == 0


@pytest.mark.parametrize('gate', ['power', 'pin', 'pwm-mode', 'enable', 'reset'])
def test_pwm_invalid_configuration_cannot_show_valid_brightness(gate):
    m, clock = setup()
    address, value = {
        'power': (m.SC + 0xC4, 0), 'pin': (m.PIN + 12, 0),
        'pwm-mode': (m.PWM + 4, 1), 'enable': (m.PWM + 76, 0),
        'reset': (m.PWM + 4, 11),
    }[gate]
    m.write_word(address, value)
    advance(m, clock, 2000)
    assert m.snapshot()['pwm'] == 0


def test_pwm_without_reset_on_mr0_does_not_report_periodic_duty():
    m, clock = setup()
    m.write_word(m.PWM + 20, 0)
    assert advance(m, clock, 1500) == 1501
    assert m.pin_output(1, 23) == 0
    assert m.snapshot()['pwm'] == 0


def test_pwm_zero_and_out_of_period_matches_follow_single_edge_rules():
    for match, expected in [(0, 0), (1000, 1), (1001, 1), (0xFFFFFFFF, 1)]:
        m, clock = setup(match)
        advance(m, clock, 2001)
        assert m.pin_output(1, 23) == expected
        assert m.pwm_duty() == expected


def test_pwm_pin_readback_uses_electrical_level_instead_of_gpio_output_latch():
    m, clock = setup()
    for us, expected in [(1, 1), (249, 0), (750, 1)]:
        advance(m, clock, us)
        assert (m.read_word(0x2009C034) >> 23) & 1 == expected


def test_pwm_open_drain_releases_high_output_and_cannot_power_led():
    m, clock = setup()
    m.write_word(m.PIN + 0x6C, 1 << 23)
    m.write_word(m.PIN + 0x4C, 2 << 14)
    advance(m, clock, 1)
    assert m.pin_output(1, 23) is None
    assert m.snapshot()['pwm'] == 0
    advance(m, clock, 249)
    assert m.pin_output(1, 23) == 0


def test_unsupported_external_counter_does_not_report_periodic_pwm():
    m, clock = setup()
    m.write_word(m.PWM + 0x70, 1)
    advance(m, clock, 2000)
    assert m.snapshot()['pwm'] == 0


def test_seeded_pwm_latch_schedule_against_independent_clock_oracle(record_property, vector_log):
    rng = random.Random(176824)
    m, clock = setup()
    counter, active, pending = 0, 250, None
    for case in range(256):
        requested = rng.randrange(1001)
        m.write_word(m.PWM + 64, requested)
        if rng.choice([False, True]):
            m.write_word(m.PWM + 80, 16)
            pending = requested
        elif pending is not None:
            # LER arms the register, not a snapshot of its value at LER write.
            pending = requested
        delta = rng.randrange(1, 2501)
        if counter + delta >= 1000 and pending is not None:
            active, pending = pending, None
        counter = (counter + delta) % 1000
        assert advance(m, clock, delta) == counter + 1, case
        assert m.pin_output(1, 23) == int(active > counter), case
        assert m.pwm_duty() == active / 1000, case
        vector_log(m, f'seed176824-case{case}',
                   [counter + 1, int(active > counter), active / 1000],
                   [m.read_word(m.PWM + 8), m.pin_output(1, 23), m.pwm_duty()],
                   {'delta_us': delta, 'written_MR4': requested, 'pending': pending},
                   11, 'UM10360 24.6.7; independent integer counter/latch oracle')
    record_property('finite_cases', 256)


def test_pwm_counter_uses_one_based_cycle_without_losing_a_period_clock():
    # UM10360 Table447: PWM resets to1. A full period still has MR0 clocks:
    # the held counter sequence is 1..MR0; actions occur on the following edge.
    m, clock = setup(duty=2, period=4)
    observed = []
    for _ in range(8):
        observed.append((advance(m, clock, 1), m.pin_output(1, 23)))
    assert observed == [(2, 1), (3, 0), (4, 0), (1, 1)] * 2


def test_compiled_pwm_registers_drive_electrical_output():
    source = '''#include <LPC17xx.h>
    int main(void) {LPC_SC->PCONP|=64;LPC_PINCON->PINSEL3=2u<<14;
      LPC_PWM1->TCR=2;LPC_PWM1->PR=24;LPC_PWM1->MR0=1000;
      LPC_PWM1->MR4=250;LPC_PWM1->LER=17;LPC_PWM1->MCR=2;
      LPC_PWM1->PCR=1u<<12;LPC_PWM1->TCR=9;while(1) {}}
    '''
    clock = Clock()
    m = Machine(Compiler().compile(source).hex, realtime=True, clock_ns=clock)
    m.resume_clock()
    m.run(10000)
    assert m.core_clock_hz() == 100000000
    advance(m, clock, 249)
    assert m.pin_output(1, 23) == 1
    advance(m, clock, 1)
    assert m.pin_output(1, 23) == 0
