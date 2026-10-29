"""Independent GPIO latch/mask/byte oracle, driven by compiled Thumb stores.

NXP UM10360 chapter9: FIOPIN replaces enabled output latch bits, FIOSET ORs,
FIOCLR clears, FIOMASK inhibits writes and FIOPIN reads. FIOSET reads latch.
Reserved/unbonded pins and undefined reads from WO FIOCLR are not asserted.
"""
import random
import struct

import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine
from fidelity_vector_support import vector_log

BOX = 0x10007000
GPIO = 0x2009C000
# Package pins transcribed from ALS board manual piggyback pinouts pp21-24.
PINS = {
    0: list(range(0, 12)) + list(range(15, 31)),
    1: [0, 1, 4, 8, 9, 10] + list(range(14, 32)),
    2: list(range(14)), 3: [25, 26], 4: [28, 29],
}


@pytest.fixture(scope='module')
def probe_hex():
    return Compiler().compile('''#include <LPC17xx.h>
int main(void) {volatile unsigned *b=(void*)0x10007000;unsigned seq=0;
 while(1) {if(b[0]!=seq) {seq=b[0];
 if(b[3]==1) *(volatile unsigned char*)b[1]=(unsigned char)b[2];
 else if(b[3]==2) *(volatile unsigned short*)b[1]=(unsigned short)b[2];
 else *(volatile unsigned*)b[1]=b[2];
 b[5]=*(volatile unsigned*)b[4];b[6]=seq;
 }} }
''').hex


@pytest.fixture
def probe(probe_hex):
    m = Machine(probe_hex)
    m.run(2000)
    m._test_sequence = 0
    return m


def write_read(m, address, value, read_address, width=4):
    m._test_sequence += 1
    m.uc.mem_write(BOX, struct.pack('<5I', m._test_sequence, address, value, width, read_address))
    m.run(500)
    result, done = struct.unpack('<2I', m.uc.mem_read(BOX + 20, 8))
    assert done == m._test_sequence
    assert m.error is None
    return result


@pytest.mark.parametrize('port', range(5))
def test_seeded_gpio_register_sequences_independent_latch_oracle(probe, port, record_property, vector_log):
    record_property('finite_cases', 500)
    m = probe
    rng = random.Random(0x176800 + port)
    valid = sum(1 << pin for pin in PINS[port])
    latch = direction = mask = 0
    base = GPIO + port * 32
    trace = []
    for index in range(500):
        reg = rng.choice([0, 0x10, 0x14, 0x18, 0x1C])
        width = rng.choice([1, 2, 4])
        byte = rng.randrange(4 // width) * width
        value = rng.getrandbits(width * 8)
        enabled = ((1 << (width * 8)) - 1) << (8 * byte)
        shifted = value << (8 * byte)
        if reg == 0:
            direction = (direction & ~enabled) | shifted
        elif reg == 0x10:
            mask = (mask & ~enabled) | shifted
        else:
            writable = enabled & ~mask & 0xFFFFFFFF
            if reg == 0x14:
                latch = (latch & ~writable) | (shifted & writable)
            elif reg == 0x18:
                latch |= shifted & writable
            else:
                latch &= ~(shifted & writable)
        readreg = rng.choice([0, 0x10, 0x14, 0x18])
        # Unconnected inputs default to documented pull-up reset mode.
        expect = {0: direction, 0x10: mask, 0x18: latch,
                  0x14: ((latch & direction) | (~direction & 0xFFFFFFFF)) & ~mask}[readreg]
        observed = write_read(m, base + reg + byte, value, base + readreg, width)
        trace.append((hex(base + reg + byte), width, hex(value), hex(observed), hex(expect)))
        vector_log(m, f'port{port}/step{index}', expect & valid, observed & valid,
                   {'seed': 0x176800 + port, 'write_address': hex(base + reg + byte), 'width': width,
                    'value': value, 'read_address': hex(base + readreg), 'valid_mask': valid}, 6,
                   'NXP UM10360 chapter9 FIOPIN/FIOSET/FIOCLR/FIOMASK, byte/halfword access')
        assert (observed ^ expect) & valid == 0, (port, index, trace[-20:], m.snapshot())


@pytest.mark.parametrize('port', range(5))
def test_pinmux_direction_and_pull_modes_over_all_bonded_pins(probe, port, record_property, vector_log):
    record_property('finite_cases', len(PINS[port]) * 4)
    m = probe
    base = GPIO + port * 32
    for pin in PINS[port]:
        bit = 1 << pin
        index, shift = port * 2 + pin // 16, 2 * (pin % 16)
        mux, pull = Machine.PIN + index * 4, Machine.PIN + 0x40 + index * 4
        # Pull-down input remains LOW despite preloading its output latch HIGH.
        write_read(m, base, 0, base)
        write_read(m, mux, 0, mux)
        write_read(m, pull, 3 << shift, pull)
        actual = write_read(m, base + 0x18, bit, base + 0x14) & bit
        vector_log(m, f'port{port}/pin{pin}/input-pulldown', 0, actual, {'latch': 1, 'direction': 0, 'pull': 3},
                   6, 'NXP UM10360 GPIO direction and PINMODE chapter8')
        assert actual == 0
        # Making that pin an output now exposes the independently retained latch.
        actual = write_read(m, base, bit, base + 0x14) & bit
        vector_log(m, f'port{port}/pin{pin}/output', bit, actual, {'latch': 1, 'direction': 1},
                   6, 'NXP UM10360 GPIO FIODIR output latch')
        assert actual == bit
        # Selecting another function disconnects the GPIO driver from LED loads.
        write_read(m, mux, 1 << shift, mux)
        vector_log(m, f'port{port}/pin{pin}/mux', None, m.pin_output(port, pin), {'function': 1},
                   6, 'NXP UM10360 PINSEL controls alternate function versus GPIO driver')
        assert m.pin_output(port, pin) is None
        # GPIO input mode with pull-up reads HIGH.
        write_read(m, mux, 0, mux)
        write_read(m, base, 0, base)
        actual = write_read(m, pull, 0, base + 0x14) & bit
        vector_log(m, f'port{port}/pin{pin}/input-pullup', bit, actual, {'direction': 0, 'pull': 0},
                   6, 'NXP UM10360 PINMODE reset pull-up mode')
        assert actual == bit


def test_fiopin_replaces_zeroes_set_clear_preserve_neighbors_and_mask(probe):
    m = probe
    m.board.connect('CNA', 'CNA1')
    write_read(m, GPIO, 0xFF0, GPIO)
    write_read(m, GPIO + 0x18, 0xFF0, GPIO + 0x18)
    assert m.snapshot()['leds'] == [True] * 8
    write_read(m, GPIO + 0x14, 0xA50, GPIO + 0x14)
    assert m.snapshot()['leds'] == [True, False, True, False, False, True, False, True]
    write_read(m, GPIO + 0x10, 0xF00, GPIO + 0x10)
    write_read(m, GPIO + 0x14, 0x5A0, GPIO + 0x14)
    assert m.snapshot()['leds'] == [False, True, False, True, False, True, False, True]
    # FIOSET read is the unmasked output latch, distinct from FIOPIN.
    assert write_read(m, GPIO + 0x18, 0, GPIO + 0x18) & 0xFF0 == 0xAA0
    assert write_read(m, GPIO + 0x18, 0, GPIO + 0x14) & 0xFF0 == 0xA0
    write_read(m, GPIO + 0x1C, 0x20, GPIO + 0x14)
    write_read(m, GPIO + 0x18, 0x10, GPIO + 0x14)
    assert m.snapshot()['leds'] == [True, False, False, True, False, True, False, True]


def test_cross_port_writes_and_read_modify_write_keep_unrelated_outputs(probe):
    m = probe
    m.board.connect('CNB', 'CNA1')
    m.board.set_jumper('JP4', '1-2')
    write_read(m, GPIO + 0x20, 15 << 23, GPIO + 0x20)
    write_read(m, GPIO + 0x40, 15 << 10, GPIO + 0x40)
    write_read(m, GPIO + 0x38, 5 << 23, GPIO + 0x34)
    write_read(m, GPIO + 0x58, 10 << 10, GPIO + 0x54)
    assert m.snapshot()['leds'] == [True, False, True, False, False, True, False, True]
    # RMW via FIOPIN includes input levels; output pins preserve their states.
    prior = m.read_word(GPIO + 0x34)
    write_read(m, GPIO + 0x34, prior | (1 << 24), GPIO + 0x34)
    assert m.snapshot()['leds'] == [True, True, True, False, False, True, False, True]


@pytest.mark.parametrize('kind', ['ring', 'reverse', 'johnson', 'up', 'down'])
def test_compiled_counter_full_period_twice_and_direction_reversal(probe_hex, kind, record_property, vector_log):
    period = 16 if kind == 'johnson' else 8 if kind in ('ring', 'reverse') else 256
    record_property('finite_cases', period * 2 + 2)
    # A separate unfamiliar firmware computes the transitions, never Python
    # writes to output GPIO. Mailbox commands gate single observable steps.
    expression = {
        'ring': '(v<<1)|(v>>7)', 'reverse': '(v>>1)|(v<<7)',
        'johnson': '(v<<1)|((~(v>>7))&1)', 'up': 'v+1', 'down': 'v-1',
    }[kind]
    reverse_expression = {
        'ring': '(v>>1)|(v<<7)', 'reverse': '(v<<1)|(v>>7)',
        'johnson': '(v>>1)|(((~v)&1)<<7)', 'up': 'v-1', 'down': 'v+1',
    }[kind]
    init = 0 if kind in ('johnson', 'up', 'down') else 1
    source = f'''#include <LPC17xx.h>
int main(void) {{volatile unsigned *b=(void*){BOX};unsigned seq=0,v={init};
 LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO0->FIOPIN=v<<4;
 while(1) {{if(b[0]!=seq) {{seq=b[0];
 if(b[1]) v={reverse_expression}; else v={expression};
 v&=255;LPC_GPIO0->FIOPIN=v<<4;b[2]=seq;}} }} }}'''
    m = Machine(Compiler().compile(source).hex)
    m.board.connect('CNA', 'CNA1')
    m.run(3000)
    value = init
    for step in range(1, period * 2 + 3):
        reverse = step > period * 2
        if reverse:
            if kind == 'ring':
                value = value // 2 + (value % 2) * 128
            elif kind == 'reverse':
                value = (value * 2) % 256 + value // 128
            elif kind == 'johnson':
                value = value // 2 + int(value % 2 == 0) * 128
            elif kind == 'up':
                value = (value - 1) % 256
            else:
                value = (value + 1) % 256
        elif kind == 'reverse':
            value = value // 2 + (value % 2) * 128
        elif kind == 'ring':
            value = (value * 2) % 256 + value // 128
        elif kind == 'johnson':
            value = (value * 2) % 256 + int(value < 128)
        elif kind == 'up':
            value = (value + 1) % 256
        else:
            value = (value - 1) % 256
        m.uc.mem_write(BOX, struct.pack('<2I', step, int(reverse)))
        m.run(500)
        expected = [bool(value & (1 << i)) for i in range(8)]
        actual = m.snapshot()['leds']
        vector_log(m, f'{kind}/step{step}', expected, actual, {'reverse': reverse, 'command': step},
                   7, 'ESD PDF pp28-29 LED counter exercises; independent 8-bit arithmetic oracle')
        assert actual == expected, (kind, step, value, m.snapshot())
        assert m.gpio[0].latch & 0xFF0 == value << 4
