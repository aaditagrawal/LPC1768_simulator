"""Manual-derived wiring probes, executed as compiled Cortex-M3 firmware.

Pin expectations below are transcribed independently from the board PDF pp.24-26,
31-37,50-52 and ESD.pdf pp.27,29,41,43-45,50 (one-based PDF page numbers).
The SRAM mailbox is test stimulus/readback; firmware performs every MMIO access.
"""
import struct

import pytest

from simulator.board import MAPPING
from simulator.compiler import Compiler
from simulator.engine import Machine


MAILBOX = 0x10007000
HEADERS = {
    'CNA': [(0, n) for n in range(4, 12)],
    'CNB': [(1, n) for n in range(23, 27)] + [(2, n) for n in range(10, 14)],
    'CNC': [(0, n) for n in range(15, 23)],
    'CND': [(0, n) for n in range(23, 29)] + [(2, 0), (2, 1)],
}


@pytest.fixture(scope='module')
def firmware():
    cache = {}

    def load(body):
        if body not in cache:
            cache[body] = Compiler().compile('#include <LPC17xx.h>\n' + body).hex
        return Machine(cache[body])

    return load


def run(m, slices=2):
    for _ in range(slices):
        m.run(2000)
    assert m.error is None
    return m.snapshot()


def command(m, value):
    m.uc.mem_write(MAILBOX, struct.pack('<I', value))
    return run(m)


def result(m, offset=4):
    return struct.unpack('<I', bytes(m.uc.mem_read(MAILBOX + offset, 4)))[0]


def configure(m, header, peripheral):
    m.board.connect(header, peripheral)
    m.board.set_jumper('JP4', '1-2')
    m.board.set_jumper('JP5', 'closed')


def test_manual_header_pin_numbers():
    for header, pins in HEADERS.items():
        actual = MAPPING['headers'][header]['pins'][:8]
        expected = [f'P{port}.{pin}' for port, pin in pins]
        if header == 'CNB':
            expected[7] = 'JP4_B'
        if header == 'CND':
            expected[3] = 'JP5_DATA'
        assert actual == expected
        assert MAPPING['headers'][header]['pins'][9] == 'GND'
    assert MAPPING['headers']['CNC']['pins'][8] == 'JP4_C'
    for header in ['CNA', 'CNB', 'CND']:
        assert MAPPING['headers'][header]['pins'][8] is None
    assert MAPPING['headers']['CNAD']['pins'][:6] == [
        'LCD0', 'LCD1', 'LCD2', 'LCD3', 'LCD_RS', 'LCD_EN']
    assert MAPPING['headers']['CNB3']['pins'][:8] == [
        'COL0', 'COL1', 'COL2', 'COL3', 'ROW0', 'ROW1', 'ROW2', 'ROW3']


@pytest.mark.parametrize('header', HEADERS)
def test_every_led_line_from_every_gpio_header(firmware, header):
    pins = HEADERS[header]
    setup = ''.join(f'LPC_GPIO{p}->FIODIR |= 1u<<{n};' for p, n in pins)
    writes = ''.join(
        f'if(v & (1u<<{i})) LPC_GPIO{p}->FIOSET=1u<<{n};'
        f'else LPC_GPIO{p}->FIOCLR=1u<<{n};' for i, (p, n) in enumerate(pins))
    m = firmware(f'int main(void) {{volatile unsigned *box=(void*){MAILBOX};'
                 f'{setup} while(1) {{unsigned v=box[0];{writes}}}}}')
    configure(m, header, 'CNA1')
    for value in [0, 255, 0x55, 0xAA] + [1 << i for i in range(8)]:
        assert command(m, value)['leds'] == [bool(value & (1 << i)) for i in range(8)]
    m.board.disconnect(header)
    assert not any(run(m)['leds'])


@pytest.mark.parametrize('header,bit,jumper', [('CNB', 7, 'JP4'), ('CND', 3, 'JP5')])
def test_port_test_jumpers_isolate_only_their_documented_line(firmware, header, bit, jumper):
    pins = HEADERS[header]
    setup = ''.join(f'LPC_GPIO{p}->FIODIR |= 1u<<{n};LPC_GPIO{p}->FIOSET=1u<<{n};'
                    for p, n in pins)
    m = firmware(f'int main(void) {{{setup} while(1) {{}}}}')
    configure(m, header, 'CNA1')
    assert all(run(m)['leds'])
    m.board.set_jumper(jumper, 'open')
    expected = [True] * 8
    expected[bit] = False
    assert run(m)['leds'] == expected


@pytest.mark.parametrize('header', HEADERS)
def test_sw2_active_low_through_any_gpio_header(firmware, header):
    port, pin = HEADERS[header][6]  # ESD p.29 explicitly specifies CNB1 pin 7.
    m = firmware(f'int main(void) {{volatile unsigned *box=(void*){MAILBOX};'
                 f'while(1) box[1]=(LPC_GPIO{port}->FIOPIN>>{pin})&1;}}')
    configure(m, header, 'CNB1')
    for pressed, expected in [(False, 1), (True, 0), (False, 1)]:
        m.board.sw2 = pressed
        m.observe()
        run(m)
        assert result(m) == expected
    m.board.sw2 = True
    m.board.disconnect(header)
    run(m)
    assert result(m) == 1  # Disconnected MCU input returns to its pull-up.


@pytest.mark.parametrize('header', HEADERS)
def test_all_keypad_rows_columns_and_release_on_any_gpio_header(firmware, header):
    columns, rows = HEADERS[header][:4], HEADERS[header][4:]
    setup = ''.join(f'LPC_GPIO{p}->FIODIR |= 1u<<{n};' for p, n in rows)
    setup += ''.join(f'LPC_GPIO{p}->FIODIR &= ~(1u<<{n});' for p, n in columns)
    drive = ''.join(f'if(v&(1u<<{i})) LPC_GPIO{p}->FIOSET=1u<<{n};'
                    f'else LPC_GPIO{p}->FIOCLR=1u<<{n};' for i, (p, n) in enumerate(rows))
    read = '|'.join(f'(((LPC_GPIO{p}->FIOPIN>>{n})&1)<<{i})' for i, (p, n) in enumerate(columns))
    m = firmware(f'int main(void) {{volatile unsigned *box=(void*){MAILBOX};'
                 f'{setup} while(1) {{unsigned v=box[0];{drive}box[1]={read};}}}}')
    configure(m, header, 'CNB3')
    for row in range(4):
        command(m, 1 << row)
        assert result(m) == 0  # External column pulldowns, even with MCU pull-ups.
        for key in range(16):
            m.board.keys = {key}
            m.observe()
            run(m)
            assert result(m) == (1 << (key % 4) if key // 4 == row else 0)
        m.board.keys.clear()
        m.observe()
        run(m)
        assert result(m) == 0
    # CNB row 4 needs JP4 1-2; other three rows remain available.
    if header == 'CNB':
        command(m, 8)
        m.board.keys = {15}
        for position, expected in [('open', 0), ('2-3', 0), ('1-2', 8)]:
            m.board.set_jumper('JP4', position)
            run(m)
            assert result(m) == expected


@pytest.mark.parametrize('channel,pin', [(4, 30), (5, 31)])
def test_adc_voltage_sweep_mux_power_and_pot4_jumper(firmware, channel, pin):
    # box[0] controls whether firmware selects analog function 3; box[2] enables ADC power.
    m = firmware(f'''int main(void) {{volatile unsigned *box=(void*){MAILBOX};
      while(1) {{
        LPC_PINCON->PINSEL3=(box[0]?3u:0u)<<{2 * (pin - 16)};
        if(box[2]) LPC_SC->PCONP|=1u<<12; else LPC_SC->PCONP&=~(1u<<12);
        LPC_ADC->ADCR=(1u<<{channel})|(1u<<21)|(1u<<24);
        box[1]=LPC_ADC->ADGDR;
      }} }}''')
    m.uc.mem_write(MAILBOX + 8, struct.pack('<I', 1))
    m.board.set_jumper('JP18', '2-3')
    for voltage, expected in [(0, 0), (0.825, 1024), (1.65, 2048), (2.475, 3071), (3.3, 4095)]:
        m.board.pots[channel] = voltage
        command(m, 1)
        raw = result(m)
        assert raw & (1 << 31)
        assert ((raw >> 4) & 4095) == expected
        assert ((raw >> 24) & 7) == channel
    command(m, 0)
    assert ((result(m) >> 4) & 4095) == 0
    command(m, 1)
    if channel == 4:
        for position, expected in [('open', 0), ('1-2', 0), ('2-3', 4095)]:
            m.board.set_jumper('JP18', position)
            run(m)
            assert ((result(m) >> 4) & 4095) == expected
    m.uc.mem_write(MAILBOX + 8, struct.pack('<I', 0))
    run(m)
    assert not result(m) & (1 << 31)


def test_board_manual_external_interrupt_toggles_ld10(firmware):
    m = firmware('''volatile unsigned on;
      void EINT2_IRQHandler(void) {LPC_SC->EXTINT=4;on^=1;
        if(on) LPC_GPIO1->FIOSET=1u<<23;else LPC_GPIO1->FIOCLR=1u<<23;}
      int main(void) {LPC_GPIO1->FIODIR=1u<<23;LPC_PINCON->PINSEL4=1u<<24;
        LPC_SC->EXTMODE=4;NVIC_EnableIRQ(EINT2_IRQn);while(1) {}}''')
    configure(m, 'CNB', 'CNB1')
    assert run(m)['pwm'] == 0
    for expected in [1, 0, 1]:
        m.board.sw2 = True
        m.observe()
        assert run(m, 3)['pwm'] == expected
        before = m.irq_count
        run(m, 3)
        assert m.irq_count == before
        m.board.sw2 = False
        m.observe()
        run(m)
    m.board.disconnect('CNB')
    assert run(m)['pwm'] == 0


@pytest.mark.parametrize('duty', [0, 10, 25, 50, 75, 100])
def test_pwm_manual_duty_levels_and_output_pinmux(firmware, duty):
    m = firmware(f'''int main(void) {{volatile unsigned *box=(void*){MAILBOX};
      LPC_SC->PCONP|=1u<<6;LPC_PWM1->MR0=1000;LPC_PWM1->MR4={duty * 10};
      LPC_PWM1->LER=0x11;LPC_PWM1->PCR=1u<<12;LPC_PWM1->TCR=9;
      while(1) LPC_PINCON->PINSEL3=box[0]?(2u<<14):0;}}''')
    configure(m, 'CNB', 'CNB1')
    assert command(m, 1)['pwm'] == pytest.approx(duty / 100)
    assert command(m, 0)['pwm'] == 0
    m.board.disconnect('CNB')
    assert command(m, 1)['pwm'] == 0


def test_lab11_keyboard_controls_pwm_with_separate_gpio_header(firmware):
    # CNB is occupied by CNB1. ESD p.41 permits another MCU header for CNB3.
    m = firmware('''int main(void) {unsigned bits;
      LPC_SC->PCONP|=1u<<6;LPC_PINCON->PINSEL3=2u<<14;
      LPC_GPIO0->FIODIR=15u<<19;LPC_GPIO0->FIOSET=1u<<19;
      LPC_PWM1->MR0=1000;LPC_PWM1->MR4=0;LPC_PWM1->LER=0x11;
      LPC_PWM1->PCR=1u<<12;LPC_PWM1->TCR=9;
      while(1) {bits=(LPC_GPIO0->FIOPIN>>15)&15;
        if(bits) {LPC_PWM1->MR4=(bits&1)?100:(bits&2)?250:(bits&4)?500:750;
          LPC_PWM1->LER=0x10;}}}''')
    configure(m, 'CNB', 'CNB1')
    m.board.connect('CNC', 'CNB3')
    assert run(m)['pwm'] == 0
    for key, expected in enumerate([0.10, 0.25, 0.50, 0.75]):
        m.board.keys = {key}
        m.observe()
        assert run(m)['pwm'] == pytest.approx(expected)
        m.board.keys.clear()
        m.observe()
        assert run(m)['pwm'] == pytest.approx(expected)


LCD_PROBE = '''
void nib(unsigned v,unsigned rs) {
 LPC_GPIO0->FIOCLR=0x1F800000;
 LPC_GPIO0->FIOSET=((v&15)<<23)|(rs<<27);
 LPC_GPIO0->FIOSET=1u<<28;LPC_GPIO0->FIOCLR=1u<<28;
}
void byte(unsigned v,unsigned rs) {nib(v>>4,rs);nib(v,rs);}
int main(void) {unsigned old=0;volatile unsigned *box=(void*)0x10007000;
 LPC_GPIO0->FIODIR=0x1F800000;
 nib(3,0);nib(3,0);nib(3,0);nib(2,0);
 byte(0x28,0);byte(0x0C,0);byte(0x06,0);byte(1,0);byte('A',1);
 while(1) {if(box[0]!=old) {old=box[0];byte(old,1);box[1]=old;}}
}
'''


def lcd_connection(m):
    m.board.connect('CND', 'CNAD')
    m.board.set_jumper('JP5', 'closed')
    m.board.set_jumper('JP16', 'closed')


def test_lcd_disconnect_retains_text_and_drops_unconnected_writes(firmware):
    m = firmware(LCD_PROBE)
    lcd_connection(m)
    assert run(m)['lcd'][0] == 'A' + ' ' * 15
    m.board.disconnect('CND')
    assert command(m, ord('B'))['lcd'][0] == 'A' + ' ' * 15
    m.board.connect('CND', 'CNAD')
    assert run(m)['lcd'][0] == 'A' + ' ' * 15
    assert command(m, ord('C'))['lcd'][0] == 'AC' + ' ' * 14
    m.board.set_jumper('JP16', 'open')
    assert run(m)['lcd'] == [' ' * 16] * 2
    m.board.set_jumper('JP16', 'closed')
    assert run(m)['lcd'][0] == 'AC' + ' ' * 14


@pytest.mark.parametrize('missing', ['cable', 'JP5', 'JP16'])
def test_lcd_requires_connection_and_jumpers_before_initialization(firmware, missing):
    m = firmware(LCD_PROBE)
    lcd_connection(m)
    if missing == 'cable':
        m.board.disconnect('CND')
    else:
        m.board.set_jumper(missing, 'open')
    assert run(m)['lcd'] != ['A' + ' ' * 15, ' ' * 16]
    if missing == 'cable':
        m.board.connect('CND', 'CNAD')
    else:
        m.board.set_jumper(missing, 'closed')
    assert run(m)['lcd'] != ['A' + ' ' * 15, ' ' * 16]
    reset = firmware(LCD_PROBE)
    lcd_connection(reset)
    assert run(reset)['lcd'] == ['A' + ' ' * 15, ' ' * 16]


SEGMENT_PROBE = '''int main(void) {unsigned d;volatile unsigned wait;
 volatile unsigned *box=(void*)0x10007000;
 LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO1->FIODIR=0x07800000;
 while(1) {for(d=0;d<4;d++) {
  LPC_GPIO1->FIOPIN=d<<23;LPC_GPIO0->FIOPIN=(box[d]&255)<<4;
  for(wait=0;wait<30;wait++);LPC_GPIO0->FIOCLR=0xFF0;
  LPC_GPIO1->FIOPIN=5<<23;
 }} }
'''


@pytest.mark.parametrize('digit', range(4))
def test_all_eight_segment_lines_on_each_bcd_selected_digit(firmware, digit):
    for bit in range(8):
        m = firmware(SEGMENT_PROBE)
        m.board.connect('CNA', 'CNA2')
        m.board.connect('CNB', 'CNB2')
        patterns = [0] * 4
        patterns[digit] = 1 << bit
        m.uc.mem_write(MAILBOX, struct.pack('<4I', *patterns))
        assert run(m, 8)['segments'] == patterns


def test_all_hexadecimal_segment_patterns_and_both_cable_disconnects(firmware):
    glyphs = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07,
              0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71]
    for pattern in glyphs:
        m = firmware(SEGMENT_PROBE)
        m.board.connect('CNA', 'CNA2')
        m.board.connect('CNB', 'CNB2')
        m.uc.mem_write(MAILBOX, struct.pack('<4I', *([pattern] * 4)))
        assert run(m, 8)['segments'] == [pattern] * 4
        for header in ['CNA', 'CNB']:
            m.board.disconnect(header)
            assert run(m)['segments'] == [0] * 4
            m.board.connect(header, 'CNA2' if header == 'CNA' else 'CNB2')


@pytest.mark.parametrize('timer,power', [(0, 1), (1, 2), (2, 22), (3, 23)])
def test_basic_timer_match_irq_executes_firmware_handler(firmware, timer, power):
    m = firmware(f'''void TIMER{timer}_IRQHandler(void) {{
      LPC_TIM{timer}->IR=1;LPC_GPIO0->FIOSET=0x10;}}
      int main(void) {{LPC_GPIO0->FIODIR=0x10;LPC_SC->PCONP|=1u<<{power};
        LPC_TIM{timer}->MR0=100;LPC_TIM{timer}->MCR=7;
        NVIC_EnableIRQ(TIMER{timer}_IRQn);LPC_TIM{timer}->TCR=1;while(1) {{}}}}''')
    m.board.connect('CNA', 'CNA1')
    assert run(m, 10)['leds'][0]
    assert m.irq_count == 1
    assert m.active_irq is None
