"""Independent board-pin display oracles (PDF pages are one-based).

ESD pp30-44, board pp24-26,31-37; HD44780U pp10-12,24-27.
All integration transactions below execute unfamiliar compiled ARM firmware.
"""
import struct
from itertools import combinations, permutations

import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine
from simulator.runtime import Runtime
from fidelity_vector_support import vector_log

BOX = 0x10007000
HEADERS = {
    'CNA': [(0, n) for n in range(4, 12)],
    'CNB': [(1, n) for n in range(23, 27)] + [(2, n) for n in range(10, 14)],
    'CNC': [(0, n) for n in range(15, 23)],
    'CND': [(0, n) for n in range(23, 29)] + [(2, 0), (2, 1)],
}


@pytest.fixture(scope='module')
def build():
    cache = {}
    def load(body):
        if body not in cache:
            cache[body] = Compiler().compile('#include <LPC17xx.h>\n' + body).hex
        m = Machine(cache[body])
        m.run(1000)
        return m
    return load


def exchange(m, *values):
    m.uc.mem_write(BOX, struct.pack('<' + 'I' * len(values), *values))
    m.run(2000)
    assert m.error is None
    return m.snapshot()


def connect(m, a, b):
    m.board.connect(a, b)
    m.board.set_jumper('JP4', '1-2')
    m.board.set_jumper('JP5', 'closed')


def lcd_machine(build):
    # Every nibble is emitted by firmware using FIOCLR/FIOSET and E edges.
    m = build('''
void nib(unsigned x,unsigned rs) {
 LPC_GPIO0->FIOCLR=0x1F800000;
 LPC_GPIO0->FIOSET=((x&15)<<23)|(rs<<27);
 LPC_GPIO0->FIOSET=1u<<28;LPC_GPIO0->FIOCLR=1u<<28;
}
int main(void) {volatile unsigned *b=(void*)0x10007000;unsigned seq=0,v;
 LPC_GPIO0->FIODIR=0x1F800000;
 while(1) {if(b[0]!=seq) {seq=b[0];v=b[1];
   if(b[3]) nib(v,b[2]); else {nib(v>>4,b[2]);nib(v,b[2]);}
   b[4]=seq;
 }} }
''')
    connect(m, 'CND', 'CNAD')
    m.board.set_jumper('JP16', 'closed')
    m._test_sequence = 0
    for nibble in [3, 3, 3, 2]:
        lcd_send(m, nibble, single=True)
    for cmd in [0x28, 0x0C, 0x06, 1]:
        lcd_send(m, cmd)
    return m


def lcd_send(m, value, rs=0, single=False):
    m._test_sequence += 1
    s = exchange(m, m._test_sequence, value, rs, int(single))
    assert int.from_bytes(m.uc.mem_read(BOX + 16, 4), 'little') == m._test_sequence
    return s['lcd']


def test_lcd_clear_restores_increment_mode(build):
    m = lcd_machine(build)
    lcd_send(m, 4)  # decrement mode
    lcd_send(m, 1)  # clear also sets I/D=1, HD44780U p26
    lcd_send(m, ord('A'), 1)
    assert lcd_send(m, ord('B'), 1) == ['AB' + ' ' * 14, ' ' * 16]


def test_lcd_return_home_accepts_dont_care_low_bit(build):
    m = lcd_machine(build)
    lcd_send(m, ord('A'), 1)
    lcd_send(m, 0xC4)
    lcd_send(m, 3)  # Return Home is 0000001x, HD44780U table6
    assert lcd_send(m, ord('Z'), 1) == ['Z' + ' ' * 15, ' ' * 16]


@pytest.mark.parametrize('entry,address,text,expected', [
    (6, 0x27, 'AB', [' ' * 16, 'B' + ' ' * 15]),
    (6, 0x67, 'AB', ['B' + ' ' * 15, ' ' * 16]),
    (4, 0x40, 'AB', [' ' * 16, 'A' + ' ' * 15]),
    (4, 0x00, 'AB', ['A' + ' ' * 15, ' ' * 16]),
])
def test_lcd_ddram_boundary_write_wrap(build, entry, address, text, expected):
    m = lcd_machine(build)
    lcd_send(m, entry)
    lcd_send(m, 0x80 | address)
    for ch in text:
        actual = lcd_send(m, ord(ch), 1)
    assert actual == expected
    # Reveal the last off-screen cell to independently verify the decrements.
    if entry == 4:
        lcd_send(m, 0x1C)
        lines = m.snapshot()['lcd']
        assert lines[0 if address == 0x40 else 1][0] == 'B'


@pytest.mark.parametrize('entry,address,expected', [
    (7, 0x00, [' ' * 16, ' ' * 16]),
    (5, 0x00, [' A' + ' ' * 14, ' ' * 16]),
])
def test_lcd_entry_mode_shift_moves_display(build, entry, address, expected):
    m = lcd_machine(build)
    lcd_send(m, entry)
    lcd_send(m, 0x80 | address)
    assert lcd_send(m, ord('A'), 1) == expected


KEY_SCAN = '''int main(void) {volatile unsigned *b=(void*)0x10007000;
 LPC_GPIO2->FIODIR=15u<<10;
 while(1) {LPC_GPIO2->FIOPIN=(b[0]&15)<<10;
 b[1]=(LPC_GPIO1->FIOPIN>>23)&15;} }
'''


def keypad_machine(build):
    m = build(KEY_SCAN)
    connect(m, 'CNB', 'CNB3')
    return m


def scan(m, rows, keys):
    m.board.keys = set(keys)
    m.observe()
    exchange(m, rows)
    return int.from_bytes(m.uc.mem_read(BOX + 4, 4), 'little')


@pytest.mark.parametrize('column', range(4))
def test_keypad_row_isolation_diodes_prevent_low_row_sinking(build, column):
    # ESD p42 D6-D9: diodes on rows, NOT one diode on every key.
    m = keypad_machine(build)
    assert scan(m, 1, {column, 4 + column}) == 1 << column
    assert not any('Conflicting driven' in w for w in m.snapshot()['warnings'])


def test_keypad_three_key_rectangle_still_ghosts_with_row_diodes(build):
    m = keypad_machine(build)
    # r0,c0 connects row0 source to col0, then row1 bus, then col1.
    assert scan(m, 1, {0, 4, 5}) == 3
    assert scan(m, 2, {0, 4, 5}) == 3
    assert scan(m, 4, {0, 4, 5}) == 0


@pytest.mark.parametrize('header', HEADERS)
def test_exhaustive_256_led_patterns_all_four_headers(build, header, record_property, vector_log):
    record_property('finite_cases', 256)
    pins = HEADERS[header]
    setup = ''.join(f'LPC_GPIO{p}->FIODIR|=1u<<{n};' for p, n in pins)
    writes = ''.join(f'if(v&(1u<<{i})) LPC_GPIO{p}->FIOSET=1u<<{n};'
                     f'else LPC_GPIO{p}->FIOCLR=1u<<{n};' for i, (p, n) in enumerate(pins))
    m = build(f'int main(void) {{volatile unsigned *b=(void*){BOX};unsigned v;'
              f'{setup} while(1) {{v=b[0];{writes}}}}}')
    connect(m, header, 'CNA1')
    for value in range(256):
        s = exchange(m, value)
        expected = [bool(value & (1 << bit)) for bit in range(8)]
        vector_log(m, f'{header}/{value:02X}', expected, s['leds'], {'mailbox': value}, 6,
                   'ALS board PDF pp24-26,34-35: CNA1 pins1-8 active-high LD2-LD9')
        assert s['leds'] == expected, (header, value, s)
        for bit, (port, pin) in enumerate(pins):
            assert bool(m.gpio[port].latch & (1 << pin)) == bool(value & (1 << bit))
    m.board.disconnect(header)
    assert exchange(m, 255)['leds'] == [False] * 8


SEG_STATIC = '''int main(void) {volatile unsigned *b=(void*)0x10007000;
 LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO1->FIODIR=15u<<23;
 while(1) {LPC_GPIO1->FIOPIN=(b[0]&15)<<23;
 LPC_GPIO0->FIOPIN=(b[1]&255)<<4;} }
'''


@pytest.mark.parametrize('digit', range(4))
def test_exhaustive_256_segment_masks_each_digit(build, digit, record_property, vector_log):
    record_property('finite_cases', 256)
    m = build(SEG_STATIC)
    connect(m, 'CNA', 'CNA2')
    connect(m, 'CNB', 'CNB2')
    # Shorten only the renderer's history horizon so complete settled states
    # can be enumerated quickly. No firmware/register/output logic is replaced.
    m.seven.window = 500
    for pattern in range(256):
        expected = [0] * 4
        expected[digit] = pattern
        s = exchange(m, digit, pattern)
        vector_log(m, f'digit{digit}/mask{pattern:02X}', expected, s['segments'],
                   {'selector': digit, 'pattern': pattern, 'renderer_window_ticks': 500}, 8,
                   'ESD PDF pp30-35; ALS PDF p37: common cathode active-high, U7 BCD selects')
        assert m.seven.last_digit == digit
        assert m.seven.last_pattern == pattern
        assert s['segments'] == expected, (digit, pattern, s)


@pytest.mark.parametrize('selector', range(4, 16))
def test_invalid_bcd_digit_selector_never_lights_a_digit(build, selector):
    m = build(SEG_STATIC)
    connect(m, 'CNA', 'CNA2')
    connect(m, 'CNB', 'CNB2')
    m.seven.window = 500
    assert exchange(m, selector, 255)['segments'] == [0] * 4


@pytest.mark.parametrize('missing_bit', [None, 0, 1, 2, 3])
def test_decoder_inputs_have_documented_external_pullups(build, missing_bit):
    m = build(SEG_STATIC)
    connect(m, 'CNA', 'CNA2')
    connect(m, 'CNB', 'CNB2')
    m.seven.window = 500
    assert exchange(m, 0, 0x5B)['segments'] == [0x5B, 0, 0, 0]
    direction = 0 if missing_bit is None else ((15 << 23) & ~(1 << (23 + missing_bit)))
    m.write_word(0x2009C020, direction)
    selector = 15 if missing_bit is None else 1 << missing_bit
    expected = [0] * 4
    if selector < 4:
        expected[selector] = 0x5B
    assert exchange(m, 0, 0x5B)['segments'] == expected


@pytest.mark.parametrize('mutation', ['data_input', 'data_mux', 'digit_cable', 'data_cable', 'wrong_header'])
def test_segment_bad_wiring_and_data_configuration_are_observable(build, mutation):
    m = build(SEG_STATIC)
    connect(m, 'CNA', 'CNA2')
    connect(m, 'CNB', 'CNB2')
    m.seven.window = 500
    assert exchange(m, 2, 0xFF)['segments'] == [0, 0, 0xFF, 0]
    if mutation == 'data_input':
        m.write_word(0x2009C000, 0)
    elif mutation == 'data_mux':
        m.write_word(Machine.PIN, 0x555500)
    elif mutation == 'digit_cable':
        m.board.disconnect('CNB')
    elif mutation == 'data_cable':
        m.board.disconnect('CNA')
    else:
        m.board.disconnect('CNA')
        m.board.connect('CNC', 'CNA2')
    # Run an empty instruction interval: repeatedly executing SEG_STATIC would
    # intentionally restore FIODIR only at startup, so mutations remain active.
    assert exchange(m, 2, 0xFF)['segments'] == [0] * 4


def test_keypad_all_keys_all_scan_orders_holds_and_release(build, record_property, vector_log):
    record_property('finite_cases', 16 * 4 * 24)
    m = keypad_machine(build)
    for order in permutations(range(4)):
        for key in range(16):
            for row in order:
                expected = 1 << (key % 4) if key // 4 == row else 0
                actual = scan(m, 1 << row, {key})
                vector_log(m, f'order{order}/key{key}/row{row}', expected, actual,
                           {'rows': 1 << row, 'keys': [key]}, 9,
                           'ESD PDF pp41-44: row-high scanning, external 15k column pulldowns')
                assert actual == expected, (order, key, row)
                assert scan(m, 1 << row, {key}) == expected  # hold is electrical, no auto-release
            assert scan(m, 15, set()) == 0


def test_keypad_all_three_key_rectangles_document_ghosting(build, record_property, vector_log):
    record_property('finite_cases', 576)
    m = keypad_machine(build)
    for rows in combinations(range(4), 2):
        for cols in combinations(range(4), 2):
            rectangle = {r * 4 + c for r in rows for c in cols}
            for absent in sorted(rectangle):
                for row in range(4):
                    expected = sum(1 << c for c in cols) if row in rows else 0
                    actual = scan(m, 1 << row, rectangle - {absent})
                    vector_log(m, f'rows{rows}/cols{cols}/absent{absent}/scan{row}', expected, actual,
                               {'rows': 1 << row, 'keys': sorted(rectangle - {absent})}, 9,
                               'ESD PDF p42 schematic D6-D9: row diodes permit rectangle ghosting')
                    assert actual == expected, (rows, cols, absent, row, actual)


@pytest.mark.parametrize('mutation', ['row_input', 'column_output_low', 'row_mux', 'cable', 'JP4'])
def test_keypad_misconfiguration_prevents_pressed_key_from_reading(build, mutation):
    m = keypad_machine(build)
    assert scan(m, 8, {15}) == 8
    if mutation == 'row_input':
        m.write_word(0x2009C040, 0)
    elif mutation == 'column_output_low':
        m.write_word(0x2009C020, 15 << 23)
    elif mutation == 'row_mux':
        m.write_word(Machine.PIN + 16, 1 << 26)
    elif mutation == 'cable':
        m.board.disconnect('CNB')
        # No external pulldowns remain; MCU inputs must explicitly use pulldown.
        m.write_word(Machine.PIN + 0x4C, 0xFF << 14)
    else:
        m.board.set_jumper('JP4', 'open')
    assert scan(m, 8, {15}) == 0


def test_lcd_state_commands_spaces_overwrite_offscreen_and_display_off(build):
    m = lcd_machine(build)
    for c in '1234567890ABCDEF!':
        lcd_send(m, ord(c), 1)
    assert m.snapshot()['lcd'] == ['1234567890ABCDEF', ' ' * 16]
    lcd_send(m, 0x18)  # shift whole display left, exposes off-screen '!'
    assert m.snapshot()['lcd'][0] == '234567890ABCDEF!'
    lcd_send(m, 2)
    lcd_send(m, 0x84)
    assert lcd_send(m, ord(' '), 1)[0] == '1234 67890ABCDEF'
    lcd_send(m, 0xC0)
    for c in 'second line':
        lcd_send(m, ord(c), 1)
    visible = m.snapshot()['lcd']
    assert visible == ['1234 67890ABCDEF', 'second line     ']
    assert lcd_send(m, 8) == [' ' * 16] * 2
    assert lcd_send(m, 12) == visible
    assert lcd_send(m, 1) == [' ' * 16] * 2
    assert lcd_send(m, ord('R'), 1) == ['R' + ' ' * 15, ' ' * 16]


@pytest.mark.parametrize('mutation', ['no_enable', 'nibble_order', 'cable', 'JP5', 'JP16', 'direction', 'mux'])
def test_lcd_bad_gpio_transactions_cannot_display_intended_letter(build, mutation):
    m = lcd_machine(build)
    if mutation == 'no_enable':
        m.write_word(0x2009C000, 0x0F800000)
    elif mutation == 'cable':
        m.board.disconnect('CND')
    elif mutation in ('JP5', 'JP16'):
        m.board.set_jumper(mutation, 'open')
    elif mutation == 'direction':
        m.write_word(0x2009C000, 0x18000000)
    elif mutation == 'mux':
        m.write_word(Machine.PIN + 4, 0x555 << 14)
    lcd_send(m, 0x14 if mutation == 'nibble_order' else ord('A'), 1)
    assert m.snapshot()['lcd'][0] != 'A' + ' ' * 15


GLYPHS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07,
          0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71]

SEG_COUNTER = '''const unsigned char g[16]={
 0x3F,6,0x5B,0x4F,0x66,0x6D,0x7D,7,0x7F,0x6F,0x77,0x7C,0x39,0x5E,0x79,0x71};
int main(void) {volatile unsigned *b=(void*)0x10007000;
 unsigned v,radix,d,top;volatile unsigned wait;
 LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO1->FIODIR=15u<<23;
 while(1) {radix=b[2];if(radix!=16) radix=10;
 top=radix==16?65536:10000;
 v=b[0];if(b[1]) v=v==0?top-1:v-1;else v=v+1==top?0:v+1;
 for(d=0;d<4;d++) {
 LPC_GPIO1->FIOPIN=5u<<23;LPC_GPIO0->FIOPIN=(unsigned)g[v%radix]<<4;
 LPC_GPIO1->FIOPIN=d<<23;
 for(wait=0;wait<30;wait++);LPC_GPIO1->FIOPIN=5u<<23;
 v/=radix;
 }} }
'''


@pytest.mark.parametrize('radix,start,down,expected', [
    (10, 0, 0, '0001'), (10, 9, 0, '0010'),
    (10, 99, 0, '0100'), (10, 999, 0, '1000'),
    (10, 9998, 0, '9999'), (10, 9999, 0, '0000'),
    (10, 0, 1, '9999'), (10, 1, 1, '0000'),
    (10, 10, 1, '0009'), (10, 100, 1, '0099'),
    (10, 1000, 1, '0999'), (16, 0xFFFF, 0, '0000'),
    (16, 0, 1, 'FFFF'), (16, 0xF, 0, '0010'),
    (16, 0x100, 1, '00FF'),
])
def test_compiled_four_digit_counter_boundaries_and_rollovers(build, radix, start, down, expected, vector_log):
    m = build(SEG_COUNTER)
    connect(m, 'CNA', 'CNA2')
    connect(m, 'CNB', 'CNB2')
    m.seven.window = 5000
    m.uc.mem_write(BOX, struct.pack('<3I', start, down, radix))
    m.run(15000)
    want = [GLYPHS[int(c, 16)] for c in reversed(expected)]
    actual = m.snapshot()['segments']
    vector_log(m, f'radix{radix}/{start}/down{down}', want, actual,
               {'initial_value': start, 'down': down, 'radix': radix, 'renderer_window_ticks': 5000},
               8, 'ESD PDF pp32-36: four-digit BCD and hexadecimal up/down counters')
    assert actual == want, (expected, m.snapshot())


@pytest.mark.parametrize('start,cursor_command,expected_address', [
    (0x27, 0x14, 0x40), (0x67, 0x14, 0x00),
    (0x40, 0x10, 0x27), (0x00, 0x10, 0x67),
])
def test_lcd_cursor_commands_cross_ddram_boundaries(build, start, cursor_command, expected_address):
    m = lcd_machine(build)
    lcd_send(m, 0x80 | start)
    lcd_send(m, cursor_command)
    lcd_send(m, ord('K'), 1)
    # Shift to expose cells39/103 when the cursor crosses backwards.
    if expected_address in (0x27, 0x67):
        lcd_send(m, 0x1C)
    row = int(expected_address >= 64)
    assert m.snapshot()['lcd'][row][0] == 'K'


def test_lcd_cgram_writes_do_not_corrupt_ddram_or_shift_display(build):
    m = lcd_machine(build)
    lcd_send(m, ord('A'), 1)
    lcd_send(m, 7)
    lcd_send(m, 0x7F)
    lcd_send(m, 0x1F, 1)
    assert m.lcd.address == 0
    assert m.snapshot()['lcd'][0] == 'A' + ' ' * 15
    lcd_send(m, 0x81)
    # Clear restores I/D but preserves S; test clear's preservation explicitly.
    lcd_send(m, 5)
    lcd_send(m, 1)
    assert lcd_send(m, ord('B'), 1)[0] == ' ' * 16


def test_short_key_pulse_between_firmware_polls_is_missed_and_hold_repeats(build):
    m = build('''int main(void) {volatile unsigned *b=(void*)0x10007000;
 LPC_GPIO2->FIODIR=15u<<10;
 while(1) {LPC_GPIO2->FIOPIN=(b[0]&15)<<10;
  if(b[2]) {b[1]=(LPC_GPIO1->FIOPIN>>23)&15;b[2]=0;}
 }}''')
    connect(m, 'CNB', 'CNB3')

    def poll(rows, keys):
        m.board.keys = set(keys)
        m.observe()
        exchange(m, rows, 0xDEAD, 1)
        value, gate = struct.unpack('<2I', m.uc.mem_read(BOX + 4, 8))
        assert gate == 0  # firmware acknowledged its polling opportunity
        return value

    assert poll(1, {15}) == 0  # pressed while a different row is scanned
    exchange(m, 8, 0, 0)      # row3 active, but firmware is not polling
    m.board.keys = {15}
    m.observe()
    m.run(1000)
    m.board.keys.clear()      # key released before the next polling opportunity
    m.observe()
    m.run(1000)
    assert poll(8, set()) == 0
    for _ in range(3):
        assert poll(8, {15}) == 8  # no simulator-imposed one-shot consumption
    assert poll(8, set()) == 0


def test_mcu_reset_during_lcd_nibble_transaction_retains_external_state_and_recovers(build):
    original = lcd_machine(build)
    lcd_send(original, ord('A'), 1)
    lcd_send(original, 2, single=True)  # first half of a function-set command
    assert original.lcd.high == (2, 0)
    rt = Runtime(start_worker=False)
    try:
        # Drive the same real Runtime reset path, retaining the connected board.
        rt.machine = original
        rt.loaded = True
        rt.control('reset')
        m = rt.machine
        assert m.snapshot()['lcd'] == ['A' + ' ' * 15, ' ' * 16]
        assert m.lcd.high == (2, 0)
        m._test_sequence = 0
        for nibble in [3, 3, 3, 2]:
            lcd_send(m, nibble, single=True)
        for command in [0x28, 0x0C, 0x06, 1]:
            lcd_send(m, command)
        assert lcd_send(m, ord('R'), 1) == ['R' + ' ' * 15, ' ' * 16]
    finally:
        rt.close()
