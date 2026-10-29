"""Exercise requirements from ESD PDF pp.35-36 and 41, using actual examples.

An independent trace decoder samples completed segment-data GPIO writes rather
than inspecting C variables or inferring which program is loaded. Virtual elapsed
time makes the one-second requirement independent of the host's CPU throughput.
"""
from pathlib import Path

import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine
from fidelity_vector_support import vector_log


ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07,
            0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71]


class Clock:
    ns = 0

    def __call__(self):
        return self.ns


def example(name, cables, jumpers=None):
    text = (ROOT / 'examples' / f'{name}.c').read_text()
    clock = Clock()
    m = Machine(Compiler().compile(text).hex, realtime=True, clock_ns=clock)
    for a, b in cables:
        m.board.connect(a, b)
    for name, value in (jumpers or {}).items():
        m.board.set_jumper(name, value)
    m.resume_clock()
    return m, clock


def segment_trace(m):
    """Trace real MMIO writes with the physical digit address present then."""
    observed = {}
    original = m.write_word

    def write(address, value, mask=0xFFFFFFFF):
        original(address, value, mask)
        if address == 0x2009C014:  # FIO0PIN: segment data, CNA -> CNA2.
            digit = (m.gpio[1].latch >> 23) & 15
            if digit < 4:
                observed[digit] = (m.gpio[0].latch >> 4) & 255

    m.write_word = write

    def sample():
        observed.clear()
        for _ in range(3):
            m.run(15000)
        assert set(observed) == {0, 1, 2, 3}, observed
        return [observed[d] for d in range(4)]

    return sample


def masks(value, radix):
    expected = []
    for _ in range(4):
        expected.append(SEGMENTS[value % radix])
        value //= radix
    return expected


def test_catalog_four_digit_binary_ring_full_period_twice(vector_log):
    m, clock = example('lab8_ring', [('CNA', 'CNA2'), ('CNB', 'CNB2')])
    original = m.write_word
    frame, states = {}, []

    def trace(address, value, mask=0xFFFFFFFF):
        original(address, value, mask)
        if address != 0x2009C014:
            return
        digit = (m.gpio[1].latch >> 23) & 15
        if digit < 4:
            frame[digit] = (m.gpio[0].latch >> 4) & 255
            if digit == 3 and len(frame) == 4:
                state = [frame[i] for i in range(4)]
                if not states or states[-1] != state:
                    states.append(state)

    m.write_word = trace
    for _ in range(500):
        m.run(5000)
        if len(states) >= 33:
            break
    assert len(states) >= 33
    for step, observed in enumerate(states[:33]):
        value = 1 << (step % 16)
        expected = [(value >> (4 * digit)) & 15 for digit in range(4)]
        vector_log(m, f'catalog-ring-step-{step}', expected, observed,
                   {'step': step, 'source': 'examples/lab8_ring.c'}, 8,
                   'ESD PDF p35: binary ring; independent one-hot position and physical mask oracle')
        assert observed == expected


@pytest.mark.parametrize('name,radix,initial,next_value', [
    ('lab8_bcd_updown', 10, 0, 1),
    ('lab8_hex_updown', 16, 0, 1),
    ('lab8_bcd_down', 10, 9999, 9998),
])
def test_manual_timer_counters_wait_one_second(name, radix, initial, next_value):
    m, clock = example(name, [('CNA', 'CNA2'), ('CNB', 'CNB2'), ('CNC', 'CNB1')])
    sample = segment_trace(m)
    assert sample() == masks(initial, radix)
    clock.ns = 999_000_000
    assert sample() == masks(initial, radix)
    clock.ns = 1_001_000_000
    assert sample() == masks(next_value, radix)
    if name != 'lab8_bcd_down':
        # Reverse during execution, then check zero underflow and max wrap.
        m.board.sw2 = True
        m.observe()
        clock.ns = 2_001_000_000
        assert sample() == masks(0, radix)
        clock.ns = 3_001_000_000
        assert sample() == masks(radix ** 4 - 1, radix)
        m.board.sw2 = False
        m.observe()
        clock.ns = 4_001_000_000
        assert sample() == masks(0, radix)


def test_manual_dice_uses_external_interrupt_and_does_not_repeat_held_edge():
    m, clock = example('lab9_dice', [('CND', 'CNAD'), ('CNB', 'CNB1')],
                       {'JP5': 'closed', 'JP16': 'closed'})
    for _ in range(5):
        m.run(15000)
    assert m.snapshot()['lcd'][0].startswith('Press SW2')
    m.board.sw2 = True
    m.observe()
    for _ in range(8):
        m.run(10000)
    assert m.irq_count == 1
    assert m.active_irq is None
    result = m.snapshot()['lcd'][1]
    assert result.startswith('Dice: ') and result[6] in '0123456'
    for _ in range(5):
        m.run(10000)
    assert m.irq_count == 1
    assert m.snapshot()['lcd'][1] == result
    m.board.sw2 = False
    m.observe()
    m.run(10000)
    m.board.sw2 = True
    m.observe()
    for _ in range(8):
        m.run(10000)
    assert m.irq_count == 2


def test_manual_dice_emits_documented_zero_through_six_range():
    m, clock = example('lab9_dice', [('CND', 'CNAD'), ('CNB', 'CNB1')],
                       {'JP5': 'closed', 'JP16': 'closed'})
    m.run(20000)
    seen = set()
    for phase in range(32):
        m.board.sw2 = False
        m.observe()
        m.run(1000 + phase * 11)
        m.board.sw2 = True
        m.observe()
        for _ in range(3):
            m.run(3000)
        line = m.snapshot()['lcd'][1]
        assert line.startswith('Dice: ')
        seen.add(int(line[6]))
    assert seen == set(range(7)), 'ESD PDF p41 explicitly specifies the range 0-6'
