"""Compile every corrected reference and exercise real firmware behavior."""
import pytest
from simulator.runtime import ROOT, CATALOG
from simulator.compiler import Compiler
from simulator.engine import Machine


@pytest.fixture(scope='session')
def examples():
    cache={}
    def load(name):
        spec=next(s for s in CATALOG if s['id']==name)
        if name not in cache:
            cache[name]=Compiler().compile((ROOT/'examples'/spec['file']).read_text()).hex
        m=Machine(cache[name])
        for a,b in spec['cables']:
            m.board.connect(a,b)
        for k,v in spec['jumpers'].items():
            m.board.set_jumper(k,v)
        return m
    return load


def advance(m, slices=5):
    for _ in range(slices):
        m.run(30000)
    return m.snapshot()


@pytest.mark.parametrize('name',[s['id'] for s in CATALOG])
def test_each_reference_compiles_and_boots(examples,name):
    m=examples(name)
    assert advance(m)['ticks']>0
    assert not m.error
    assert m.pwm_duty()>0 if name=='lab11_pwm' else m.gpio_events>0


def test_message_text_from_lcd_firmware(examples):
    m=examples('lab9_message')
    assert advance(m)['lcd']==['MIT Manipal     ','LPC1768 Lab     ']


def test_keypad_and_calculator_firmware(examples):
    m=examples('lab9_calculator')
    advance(m)
    for key in [3,10,4,14]: # 3 + 4 =
        m.board.keys.add(key)
        m.observe()
        advance(m,2)
        m.board.keys.clear()
        m.observe()
        advance(m,2)
    assert m.snapshot()['lcd'][1].startswith('3+4=7')


def test_adc_lcd_and_jp18_gate(examples):
    m=examples('lab10_adc5')
    m.board.pots[5]=3.3
    s=advance(m,15)
    assert s['lcd'][1].startswith('4095 3.300V')
    m.board.pots[5]=0
    assert advance(m,15)['lcd'][1].startswith('0 0.000V')
    m=examples('lab10_difference')
    m.board.pots={4:3.3,5:0.0}
    assert advance(m,15)['lcd'][1].startswith('4095 counts')
    m.board.set_jumper('JP18','open')
    assert advance(m,15)['lcd'][1].startswith('0 counts')


def test_pwm_interrupt_sweep(examples):
    m=examples('lab11_pwm')
    first=advance(m,3)
    later=advance(m,30)
    assert later['interrupts']>first['interrupts']
    assert later['pwm'] != first['pwm']
    assert 0 < later['pwm'] < 1


def wait_until(m,predicate,slices=50):
    for _ in range(slices):
        s=advance(m,1)
        if predicate(s):
            return s
    raise AssertionError(f'Firmware did not reach the expected output: {m.snapshot()}')


def led_value(s):
    return sum(int(on)<<i for i,on in enumerate(s['leds']))


def test_led_blink_sequence_and_binary_counter(examples):
    m=examples('lab6_blink')
    wait_until(m,lambda s:led_value(s)==255)
    wait_until(m,lambda s:led_value(s)==0)
    m=examples('lab7_sequence')
    wait_until(m,lambda s:led_value(s)==1)
    wait_until(m,lambda s:led_value(s)==3)
    wait_until(m,lambda s:led_value(s)==7)
    m=examples('lab7_binary')
    wait_until(m,lambda s:led_value(s)==1)
    wait_until(m,lambda s:led_value(s)==2)


def test_switch_and_ring_reference_behaviors(examples):
    m=examples('lab6_switch')
    advance(m,2)
    m.board.sw2=True
    m.observe()
    wait_until(m,lambda s:led_value(s)==1)
    m.board.sw2=False
    m.observe()
    wait_until(m,lambda s:led_value(s)==0)
    m=examples('lab7_ring')
    wait_until(m,lambda s:led_value(s)==1)
    for value in [2,4,8]:
        m.board.sw2=True
        m.observe()
        wait_until(m,lambda s:led_value(s)==value)
        advance(m,2)
        assert led_value(m.snapshot())==value # holding does not repeat an edge
        m.board.sw2=False
        m.observe()
        advance(m,2)


def test_sw2_dice_reference(examples):
    m=examples('lab9_dice')
    advance(m)
    m.board.sw2=True
    m.observe()
    s=wait_until(m,lambda s:s['lcd'][1].startswith('Dice: '))
    assert s['lcd'][1][6] in '0123456'  # ESD PDF p41's explicit range
    text=s['lcd'][1]
    assert advance(m,4)['lcd'][1]==text


def test_keycode_and_subtraction_reference(examples):
    m=examples('lab9_keypad')
    advance(m)
    m.board.keys.add(15)
    m.observe()
    assert wait_until(m,lambda s:s['lcd'][1].startswith('Key: F'))
    m=examples('lab9_calculator')
    advance(m)
    for key in [2,11,8,14]:
        m.board.keys.add(key)
        m.observe()
        advance(m,2)
        m.board.keys.clear()
        m.observe()
        advance(m,2)
    assert m.snapshot()['lcd'][1].startswith('2-8=-6')
