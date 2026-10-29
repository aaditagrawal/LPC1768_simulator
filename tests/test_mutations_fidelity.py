"""Bad firmware must lose the positive control's physical result.

These mutate C/register operations, never the simulator or its expected model.
Board PDF pp24-26,31-37; UM10360 ch8/9/24 define the independent oracles.
"""
import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine


LED = '''#include <LPC17xx.h>
int main(void) {LPC_GPIO0->FIODIR=0xFF0; LPC_GPIO0->FIOPIN=0x55u<<4;
while(1) {}}'''

MUTANTS = [
    ('gpio-mask', '0xFF0', '0xF0', True),
    ('gpio-shift', '0x55u<<4', '0x55u<<5', True),
    ('gpio-port', 'LPC_GPIO0->FIOPIN', 'LPC_GPIO1->FIOPIN', True),
    ('gpio-direction', 'FIODIR=0xFF0', 'FIODIR=0', True),
    ('gpio-pinsel', 'while(1)', 'LPC_PINCON->PINSEL0=0xFFFFu<<8;while(1)', True),
    ('missing-cable', 'while(1)', 'while(1)', False),
]


@pytest.fixture(scope='module')
def compile_c():
    cache = {}

    def compile(source):
        if source not in cache:
            cache[source] = Compiler().compile(source).hex
        return cache[source]

    return compile


def execute(hex, cables=()):
    m = Machine(hex)
    for a, b in cables:
        m.board.connect(a, b)
    m.run(4000)
    assert not m.error
    return m


def test_led_positive_control(compile_c):
    m = execute(compile_c(LED), [('CNA', 'CNA1')])
    assert m.snapshot()['leds'] == [True, False] * 4


@pytest.mark.parametrize('name,before,after,cable', MUTANTS, ids=[v[0] for v in MUTANTS])
def test_led_firmware_mutations_are_observable(compile_c, name, before, after, cable):
    m = execute(compile_c(LED.replace(before, after)), [('CNA', 'CNA1')] if cable else [])
    assert m.snapshot()['leds'] != [True, False] * 4, name


@pytest.mark.parametrize('selector', [4, 5, 8, 15])
def test_invalid_sevensegment_selector_mutation_has_no_valid_digit(compile_c, selector):
    source = f'''#include <LPC17xx.h>
    int main(void) {{LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO1->FIODIR=15u<<23;
    LPC_GPIO0->FIOPIN=0x3Fu<<4;LPC_GPIO1->FIOPIN={selector}u<<23;while(1) {{}}}}'''
    m = execute(compile_c(source), [('CNA', 'CNA2'), ('CNB', 'CNB2')])
    assert m.snapshot()['segments'] == [0] * 4


PWM = '''#include <LPC17xx.h>
int main(void) {LPC_SC->PCONP|=64;LPC_PINCON->PINSEL3=2u<<14;
LPC_PWM1->TCR=2;LPC_PWM1->MR0=1000;LPC_PWM1->MR4=250;
LPC_PWM1->MCR=2;LPC_PWM1->PCR=1u<<12;LPC_PWM1->LER=17;
LPC_PWM1->TCR=9;while(1) {}}'''


@pytest.mark.parametrize('before,after', [
    ('MR4=250', 'MR3=250'),
    ('PCONP|=64', 'PCONP&=~64u'),
    ('PCR=1u<<12', 'PCR=0'),
    ('MCR=2', 'MCR=0'),
], ids=['wrong-match', 'missing-power', 'missing-output-enable', 'missing-period-reset'])
def test_pwm_firmware_mutations_are_observable(compile_c, before, after):
    m = execute(compile_c(PWM.replace(before, after)), [('CNB', 'CNB1')])
    assert m.snapshot()['pwm'] != .25


def test_pwm_positive_control(compile_c):
    m = execute(compile_c(PWM), [('CNB', 'CNB1')])
    assert m.snapshot()['pwm'] == .25


def test_missing_latch_update_mutation_keeps_old_waveform(compile_c):
    # Old initialization's LER is consumed by running several real periods.
    # The mutable mailbox triggers firmware writes, not direct model mutation.
    source = PWM.replace('while(1) {}', '''while(1) {
      if(*(volatile unsigned*)0x10007000) {LPC_PWM1->MR4=750;}
    }''')
    m = execute(compile_c(source), [('CNB', 'CNB1')])
    for _ in range(20):
        if not m.read_word(m.PWM + 80):
            break
        m.run(4000)
    assert not m.read_word(m.PWM + 80)
    m.uc.mem_write(0x10007000, (1).to_bytes(4, 'little'))
    m.run(8000)
    assert m.snapshot()['pwm'] == .25
    valid = source.replace('MR4=750;', 'MR4=750;LPC_PWM1->LER=16;')
    m = execute(compile_c(valid), [('CNB', 'CNB1')])
    for _ in range(20):
        if not m.read_word(m.PWM + 80):
            break
        m.run(4000)
    assert not m.read_word(m.PWM + 80)
    m.uc.mem_write(0x10007000, (1).to_bytes(4, 'little'))
    m.run(8000)
    assert m.snapshot()['pwm'] == .75


LCD = '''#include <LPC17xx.h>
void nib(unsigned v,unsigned rs) {
 LPC_GPIO0->FIOCLR=0x1F800000;LPC_GPIO0->FIOSET=(v<<23)|(rs<<27);
 LPC_GPIO0->FIOSET=1u<<28;LPC_GPIO0->FIOCLR=1u<<28;}
void byte(unsigned v,unsigned rs) {nib(v>>4,rs);nib(v&15,rs);}
int main(void) {LPC_GPIO0->FIODIR=0x1F800000;
 nib(3,0);nib(3,0);nib(3,0);nib(2,0);byte(0x28,0);byte(0x0C,0);
 byte(0x06,0);byte(0x01,0);byte('T',1);while(1) {}}
'''


@pytest.mark.parametrize('name,before,after', [
    ('nibble-order', 'nib(v>>4,rs);nib(v&15,rs);', 'nib(v&15,rs);nib(v>>4,rs);'),
    ('missing-enable', 'LPC_GPIO0->FIOSET=1u<<28;', ''),
    ('wrong-rs', "byte('T',1)", "byte('T',0)"),
], ids=['nibble-order', 'missing-enable', 'wrong-rs'])
def test_lcd_firmware_mutations_do_not_display_intended_text(compile_c, name, before, after):
    def observe(source):
        m = Machine(compile_c(source))
        m.board.connect('CND', 'CNAD')
        m.board.set_jumper('JP5', 'closed')
        m.board.set_jumper('JP16', 'closed')
        m.run(5000)
        return m.snapshot()['lcd']
    assert observe(LCD) == ['T'.ljust(16), ' ' * 16]
    assert observe(LCD.replace(before, after)) != ['T'.ljust(16), ' ' * 16], name


def test_incorrect_counter_rollover_mutation_is_observable(compile_c):
    source = '''#include <LPC17xx.h>
    int main(void) {unsigned v=255;LPC_GPIO0->FIODIR=0xFF0;
      v=(v+1)%256;LPC_GPIO0->FIOPIN=v<<4;while(1) {}}'''
    assert execute(compile_c(source), [('CNA', 'CNA1')]).snapshot()['leds'] == [False] * 8
    mutant = source.replace('%256', '%255')
    assert execute(compile_c(mutant), [('CNA', 'CNA1')]).snapshot()['leds'] != [False] * 8


def test_improper_keyboard_scan_mutation_is_observable(compile_c):
    source = '''#include <LPC17xx.h>
    int main(void) {LPC_GPIO2->FIODIR=15u<<10;LPC_GPIO2->FIOPIN=1u<<10;
      while(1) *(volatile unsigned*)0x10007000=(LPC_GPIO1->FIOPIN>>23)&15;}
    '''

    def result(text):
        m = Machine(compile_c(text))
        m.board.connect('CNB', 'CNB3')
        m.board.set_jumper('JP4', '1-2')
        m.board.keys = {3}
        m.run(4000)
        return int.from_bytes(m.uc.mem_read(0x10007000, 4), 'little')

    assert result(source) == 8
    assert result(source.replace('FIOPIN=1u<<10', 'FIOPIN=1u<<11')) != 8


def test_missing_lcd_data_jumper_mutation_is_observable(compile_c):
    def result(jumper):
        m = Machine(compile_c(LCD))
        m.board.connect('CND', 'CNAD')
        m.board.set_jumper('JP16', 'closed')
        m.board.set_jumper('JP5', jumper)
        m.run(5000)
        return m.snapshot()['lcd']
    assert result('closed') == ['T'.ljust(16), ' ' * 16]
    assert result('open') != ['T'.ljust(16), ' ' * 16]
