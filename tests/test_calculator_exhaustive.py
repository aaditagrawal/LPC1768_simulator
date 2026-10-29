"""All 200 single-digit expressions through the catalogue calculator's actual
key matrix scans, ARM arithmetic, GPIO LCD edges, and rendered 16x2 contents.
This program uses E=equals/F=clear; calculator_timer.c has F=equals/E=restart.
"""
from pathlib import Path

import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine
from simulator.runtime import Runtime
from fidelity_vector_support import vector_log


@pytest.fixture(scope='module')
def calculator():
    source = Path(__file__).resolve().parents[1] / 'examples/lab9_calculator.c'
    m = Machine(Compiler().compile(source.read_text()).hex)
    for a, b in [('CND', 'CNAD'), ('CNB', 'CNB3')]:
        m.board.connect(a, b)
    for name, value in [('JP5', 'closed'), ('JP16', 'closed'), ('JP4', '1-2')]:
        m.board.set_jumper(name, value)
    m.run(20000)
    assert m.snapshot()['lcd'][0] == 'A:+ B:- E:= F:C '
    return m


def press(m, key, expected):
    m.board.keys = {key}
    m.observe()
    for _ in range(20):
        m.run(1000)
        if m.snapshot()['lcd'][1].rstrip() == expected:
            break
    else:
        raise AssertionError((key, expected, m.snapshot()))
    m.board.keys.clear()
    m.observe()
    m.run(1000)


@pytest.mark.parametrize('operator', ['+', '-'])
@pytest.mark.parametrize('a', range(10))
@pytest.mark.parametrize('b', range(10))
def test_all_200_single_digit_expressions(calculator, a, operator, b, record_property, vector_log):
    record_property('finite_cases', 1)
    m = calculator
    press(m, 15, '')
    press(m, a, str(a))
    press(m, 10 if operator == '+' else 11, f'{a}{operator}')
    press(m, b, f'{a}{operator}{b}')
    # Arithmetic oracle is Python integer arithmetic, independent of C and MCU.
    result = a + b if operator == '+' else a - b
    expected = f'{a}{operator}{b}={result}'
    press(m, 14, expected)
    want = ['A:+ B:- E:= F:C ', expected.ljust(16)]
    actual = m.snapshot()['lcd']
    vector_log(m, f'{a}{operator}{b}', want, actual,
               {'keys_in_order': [15, a, 10 if operator == '+' else 11, b, 14],
                'schedule': 'press, execute until LCD acknowledges, release, execute1000 instructions'}, 9,
               'ESD PDF p44 calculator exercise; catalogue firmware defines E=equals/F=clear')
    assert actual == want


def test_invalid_sequence_missing_equals_hold_and_clear_during_entry(calculator):
    m = calculator
    press(m, 15, '')
    for key in [10, 11, 12, 14]:
        press(m, key, '')
    press(m, 3, '3')
    press(m, 4, '3')  # only an operator is accepted at this stage
    press(m, 10, '3+')
    press(m, 11, '3+')
    press(m, 4, '3+4')
    m.run(30000)
    assert m.snapshot()['lcd'][1].rstrip() == '3+4'
    press(m, 14, '3+4=7')
    m.board.keys = {14}
    for _ in range(3):
        m.run(3000)
        assert m.snapshot()['lcd'][1].rstrip() == '3+4=7'
    m.board.keys.clear()
    m.observe()
    m.run(1000)
    press(m, 15, '')
    press(m, 9, '9')
    press(m, 15, '')


def test_runtime_reset_during_calculator_entry_recovers_from_firmware_initialization(calculator):
    rt = Runtime(start_worker=False)
    try:
        rt.load(calculator.hex_text)
        for a, b in [('CND', 'CNAD'), ('CNB', 'CNB3')]:
            rt.physical({'action': 'connect', 'a': a, 'b': b})
        for name, value in [('JP5', 'closed'), ('JP16', 'closed'), ('JP4', '1-2')]:
            rt.physical({'action': 'jumper', 'name': name, 'value': value})
        rt.machine.run(20000)
        press(rt.machine, 7, '7')
        press(rt.machine, 11, '7-')
        rt.control('reset')
        # Reset is an MCU operation; the external LCD has its own retained RAM.
        assert rt.snapshot()['lcd'] == ['A:+ B:- E:= F:C ', '7-'.ljust(16)]
        rt.machine.run(20000)
        assert rt.snapshot()['lcd'] == ['A:+ B:- E:= F:C ', ' ' * 16]
        press(rt.machine, 2, '2')
        press(rt.machine, 10, '2+')
        press(rt.machine, 3, '2+3')
        press(rt.machine, 14, '2+3=5')
    finally:
        rt.close()
