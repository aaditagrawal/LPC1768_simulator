"""CND keypad input must share the board with PWM through a separate CNB cable."""
from pathlib import Path
import time

import pytest

from simulator.compiler import Compiler
from simulator.runtime import Runtime


SOURCE = Path(__file__).resolve().parents[1] / 'examples/pwm_keypad_timer.c'


@pytest.fixture(scope='module')
def firmware():
    return Compiler().compile(SOURCE.read_text()).hex


@pytest.fixture
def board(firmware):
    rt = Runtime()
    try:
        rt.load(firmware)
        for a, b in [('CNB', 'CNB1'), ('CND', 'CNB3')]:
            rt.physical(dict(action='connect', a=a, b=b))
        rt.physical(dict(action='jumper', name='JP5', value='closed'))
        rt.control('run')
        wait_duty(rt, .1)
        yield rt
    finally:
        rt.close()


def wait_duty(rt, expected, timeout=.8):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        s = rt.snapshot()
        assert s['error'] is None
        if s['pwm'] == pytest.approx(expected):
            return s
        time.sleep(.005)
    raise AssertionError(f'Expected duty {expected}, got {rt.snapshot()}')


@pytest.mark.parametrize('key,duty', [(1, .25), (2, .5), (3, .75), (0, .1)])
def test_row_zero_keys_select_their_pwm_levels_and_hold_after_release(board, key, duty):
    board.physical(dict(action='key', key=key, pressed=True))
    wait_duty(board, duty)
    board.physical(dict(action='key', key=key, pressed=False))
    time.sleep(.03)
    assert board.snapshot()['pwm'] == pytest.approx(duty)
    m = board.machine
    assert m.peripheral_clock_hz(m.PWM) / (m.regs[m.PWM + 0xC] + 1) / m.pwm_latched[0] == 1000


def test_other_rows_are_ignored_and_jp5_controls_fourth_column(board):
    for key in [4, 8, 12]:
        board.physical(dict(action='key', key=key, pressed=True))
        time.sleep(.05)
        assert board.snapshot()['pwm'] == pytest.approx(.1)
        board.physical(dict(action='key', key=key, pressed=False))
    board.physical(dict(action='jumper', name='JP5', value='open'))
    board.physical(dict(action='key', key=3, pressed=True))
    time.sleep(.05)
    assert board.snapshot()['pwm'] == pytest.approx(.1)
    board.physical(dict(action='key', key=3, pressed=False))
    board.physical(dict(action='jumper', name='JP5', value='closed'))
    board.physical(dict(action='key', key=3, pressed=True))
    wait_duty(board, .75)


def test_pwm_output_requires_the_cnb_to_cnb1_cable(board):
    board.physical(dict(action='key', key=2, pressed=True))
    wait_duty(board, .5)
    board.physical(dict(action='disconnect', header='CNB'))
    assert board.snapshot()['pwm'] == 0
