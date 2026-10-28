"""The user's F-equals/E-restart calculator, through real elapsed-time firmware."""
from pathlib import Path
import time

import pytest

from simulator.compiler import Compiler
from simulator.runtime import Runtime


SOURCE = Path(__file__).resolve().parents[1] / 'examples/calculator_timer.c'


@pytest.fixture(scope='module')
def calculator_hex():
    return Compiler().compile(SOURCE.read_text()).hex


def wait_for(rt, predicate, timeout=1.5):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        state = rt.snapshot()
        assert state['error'] is None
        if predicate(state):
            return state
        time.sleep(.005)
    raise AssertionError(f'Calculator did not update: {rt.snapshot()}')


def press(rt, key, expected):
    rt.physical(dict(action='key', key=key, pressed=True))
    # This program deliberately returns a key on release, after debouncing it.
    time.sleep(.06)
    rt.physical(dict(action='key', key=key, pressed=False))
    return wait_for(rt, lambda s: s['lcd'][1].rstrip() == expected)


@pytest.fixture
def calculator(calculator_hex):
    rt = Runtime()
    try:
        rt.load(calculator_hex)
        for a, b in [('CND', 'CNAD'), ('CNB', 'CNB3')]:
            rt.physical(dict(action='connect', a=a, b=b))
        for name, value in [('JP5', 'closed'), ('JP16', 'closed'), ('JP4', '1-2')]:
            rt.physical(dict(action='jumper', name=name, value=value))
        started = time.perf_counter()
        rt.control('run')
        wait_for(rt, lambda s: s['lcd'][0].rstrip() == 'Enter A op B =')
        assert time.perf_counter() - started < 1.5
        yield rt
    finally:
        rt.close()


@pytest.mark.parametrize('a,operator,b,expected', [
    (3, 10, 4, '3+4=7'), (2, 11, 8, '2-8=-6'),
    (9, 10, 9, '9+9=18'), (0, 11, 9, '0-9=-9'),
    (5, 11, 5, '5-5=0'),
])
def test_signed_arithmetic_and_f_equals_e_restart(calculator, a, operator, b, expected):
    rt = calculator
    op = '+' if operator == 10 else '-'
    press(rt, a, str(a))
    press(rt, operator, f'{a}{op}')
    press(rt, b, f'{a}{op}{b}')
    # E is not equals in this user's program.
    press(rt, 14, f'{a}{op}{b}')
    press(rt, 15, expected)
    press(rt, 14, '')
    wait_for(rt, lambda s: s['lcd'][0].rstrip() == 'Enter A op B =')


def test_key_is_reported_only_after_release_and_unrelated_keys_are_ignored(calculator):
    rt = calculator
    press(rt, 12, '')
    rt.physical(dict(action='key', key=7, pressed=True))
    time.sleep(.12)
    assert rt.snapshot()['lcd'][1] == ' ' * 16
    rt.physical(dict(action='key', key=7, pressed=False))
    wait_for(rt, lambda s: s['lcd'][1].rstrip() == '7')
