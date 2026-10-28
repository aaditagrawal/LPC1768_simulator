"""Every peripheral assertion below is driven by genuinely compiled ARM firmware."""
import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine, FirmwareError


@pytest.fixture(scope='session')
def compile_c():
    cache = {}
    compiler = Compiler()
    def build(body):
        source = '#include <LPC17xx.h>\n' + body
        if source not in cache:
            cache[source] = compiler.compile(source).hex
        return cache[source]
    return build


def machine(compile_c, body, cables=(), jumpers=None):
    m = Machine(compile_c(body))
    for a, b in cables:
        m.board.connect(a, b)
    for k, v in (jumpers or {}).items():
        m.board.set_jumper(k, v)
    return m


def test_real_firmware_led_and_disconnect(compile_c):
    m = machine(compile_c, '''int main(void) {
      SystemInit(); SystemCoreClockUpdate(); LPC_GPIO0->FIODIR=0xFF0;
      LPC_GPIO0->FIOSET=0xA50; while(1) {} }
    ''', [('CNA','CNA1')])
    m.run(20000)
    assert m.gpio[0].latch & 0xFF0 == 0xA50
    assert m.snapshot()['leds'] == [True,False,True,False,False,True,False,True]
    assert m.gpio_events > 0
    m.board.disconnect('CNA')
    assert m.snapshot()['leds'] == [False]*8
    assert m.gpio[0].latch & 0xFF0 == 0xA50


def test_switch_input_is_read_by_firmware(compile_c):
    m = machine(compile_c, '''int main(void) {
      LPC_GPIO0->FIODIR=0x10;
      while(1) { if(LPC_GPIO2->FIOPIN & (1<<12)) LPC_GPIO0->FIOSET=0x10;
        else LPC_GPIO0->FIOCLR=0x10; } }
    ''', [('CNA','CNA1'),('CNB','CNB1')])
    m.run(10000)
    assert m.snapshot()['leds'][0]
    m.board.sw2 = True
    m.run(10000)
    assert not m.snapshot()['leds'][0]
    m.board.disconnect('CNB')
    m.run(10000)
    assert m.snapshot()['leds'][0]


def test_pinmux_mask_and_byte_access(compile_c):
    m = machine(compile_c, '''int main(void) {
      LPC_GPIO0->FIODIR=0xFF0;
      *((volatile unsigned char*)0x2009C019)=0x05;
      LPC_GPIO0->FIOMASK=0x10; LPC_GPIO0->FIOSET=0xF0;
      LPC_PINCON->PINSEL0=1<<10; while(1) {} }
    ''', [('CNA','CNA1')])
    m.run(20000)
    assert m.gpio[0].latch & 0xFF0 == 0x5E0
    assert m.snapshot()['leds'] == [False,False,True,True,True,False,True,False]


LCD_DRIVER = '''
void nib(unsigned v, unsigned rs) {
 LPC_GPIO0->FIOPIN=(v<<23)|(rs<<27);
 LPC_GPIO0->FIOSET=1<<28; LPC_GPIO0->FIOCLR=1<<28;
}
void byte(unsigned v, unsigned rs) { nib(v>>4,rs); nib(v&15,rs); }
void init(void) { LPC_GPIO0->FIODIR=0x1F800000;
 nib(3,0); nib(3,0); nib(3,0); nib(2,0);
 byte(0x28,0); byte(0x0C,0); byte(0x06,0); byte(1,0); }
'''


def test_lcd_gpio_edges_and_jumpers(compile_c):
    body = LCD_DRIVER + '''int main(void) {init(); byte('H',1); byte('i',1);
      byte(0xC0,0); byte('2',1); while(1) {} }'''
    m = machine(compile_c, body, [('CND','CNAD')], {'JP5':'closed','JP16':'closed'})
    m.run(20000)
    assert m.snapshot()['lcd'] == ['Hi              ','2               ']
    m.board.set_jumper('JP16','open')
    assert m.snapshot()['lcd'] == [' '*16]*2
    m = machine(compile_c, body, [('CND','CNAD')], {'JP16':'closed'})
    m.run(20000)
    assert m.snapshot()['lcd'] != ['Hi              ','2               ']


def test_keypad_rows_and_jp4(compile_c):
    m = machine(compile_c, '''int main(void) {
      LPC_GPIO2->FIODIR=0x3C00; LPC_GPIO0->FIODIR=0xFF0;
      while(1) { LPC_GPIO2->FIOPIN=1<<13;
      LPC_GPIO0->FIOPIN=((LPC_GPIO1->FIOPIN>>23)&15)<<4; } }
    ''', [('CNB','CNB3'),('CNA','CNA1')], {'JP4':'1-2'})
    m.board.keys.add(14) # row 3, column 2
    m.run(10000)
    assert m.snapshot()['leds'][2]
    assert sum(m.snapshot()['leds']) == 1
    m.board.set_jumper('JP4','open')
    m.run(10000)
    assert not any(m.snapshot()['leds'])


def test_seven_segment_all_gpio_transitions(compile_c):
    m = machine(compile_c, '''const unsigned a[4]={0x06,0x5B,0x4F,0x66};
      int main(void) { unsigned d; volatile unsigned wait;
      LPC_GPIO0->FIODIR=0xFF0; LPC_GPIO1->FIODIR=0x07800000;
      while(1) { for(d=0;d<4;d++) { LPC_GPIO1->FIOPIN=d<<23;
        LPC_GPIO0->FIOPIN=a[d]<<4;
        for(wait=0;wait<30;wait++); LPC_GPIO0->FIOCLR=0xFF0;
        LPC_GPIO1->FIOPIN=5<<23; } } }
    ''', [('CNA','CNA2'),('CNB','CNB2')])
    m.run(30000)
    assert m.snapshot()['segments'] == [0x06,0x5B,0x4F,0x66]
    m.board.disconnect('CNA')
    assert m.snapshot()['segments'] == [0]*4


def test_adc_actual_read_changes_leds(compile_c):
    m = machine(compile_c, '''int main(void) {
      unsigned v; LPC_SC->PCONP |= 1<<12;
      LPC_PINCON->PINSEL3 |= 0xF0000000; LPC_GPIO0->FIODIR=0xFF0;
      while(1) {LPC_ADC->ADCR=(1<<5)|(1<<21)|(1<<24);
      while(!(LPC_ADC->ADGDR & (1u<<31)));
      v=(LPC_ADC->ADGDR>>4)&4095; LPC_GPIO0->FIOPIN=(v>>4)<<4; } }
    ''', [('CNA','CNA1')])
    m.board.pots[5] = 0
    m.run(10000)
    assert not any(m.snapshot()['leds'])
    m.board.pots[5] = 3.3
    m.run(10000)
    assert all(m.snapshot()['leds'])


def test_pwm_duty_is_firmware_controlled(compile_c):
    m = machine(compile_c, '''int main(void) {
      LPC_SC->PCONP|=1<<6; LPC_PINCON->PINSEL3=2<<14;
      LPC_PWM1->MR0=1000; LPC_PWM1->MR4=250;
      LPC_PWM1->PCR=1<<12; LPC_PWM1->LER=0x11; LPC_PWM1->TCR=9;
      while(1) {} }
    ''', [('CNB','CNB1')])
    m.run(10000)
    assert m.snapshot()['pwm'] == pytest.approx(.25)
    m.board.disconnect('CNB')
    assert m.snapshot()['pwm'] == 0


def test_hex_rejects_corruption_and_bad_vectors():
    with pytest.raises(FirmwareError):
        Machine(':00000001FE\n')


def test_unknown_register_is_error(compile_c):
    m = machine(compile_c, '''int main(void) {
      *(volatile unsigned*)0x40012340=42; while(1) {} }''')
    with pytest.raises(FirmwareError, match='Unsupported'):
        m.run(10000)


def test_eint2_handler_executes_and_returns(compile_c):
    m = machine(compile_c, '''volatile unsigned hit=0;
      void EINT2_IRQHandler(void) { LPC_SC->EXTINT=4; hit++;
        LPC_GPIO0->FIOSET=0x10; }
      int main(void) { LPC_GPIO0->FIODIR=0x30;
        LPC_PINCON->PINSEL4=1<<24; LPC_SC->EXTMODE=4;
        NVIC_EnableIRQ(EINT2_IRQn);
        while(1) { if(hit) LPC_GPIO0->FIOSET=0x20; } }
    ''', [('CNB','CNB1'),('CNA','CNA1')])
    m.run(10000)
    assert not any(m.snapshot()['leds'])
    m.board.sw2 = True
    m.observe()
    for _ in range(5):
        m.run(10000)
    assert m.snapshot()['leds'][:2] == [True,True]
    assert m.irq_count == 1
    assert m.active_irq is None


def test_timer_interrupt_calls_real_handler(compile_c):
    m = machine(compile_c, '''void TIMER0_IRQHandler(void) {
      LPC_TIM0->IR=1; LPC_GPIO0->FIOSET=0x10; }
      int main(void) { LPC_GPIO0->FIODIR=0x10; LPC_SC->PCONP|=2;
        LPC_TIM0->MR0=100; LPC_TIM0->MCR=7;
        NVIC_EnableIRQ(TIMER0_IRQn); LPC_TIM0->TCR=1; while(1) {} }
    ''', [('CNA','CNA1')])
    for _ in range(5):
        m.run(10000)
    assert m.snapshot()['leds'][0]
    assert m.irq_count == 1
    assert m.active_irq is None


def test_held_level_interrupt_reenters_ram_only_handler(compile_c):
    m=machine(compile_c, '''volatile unsigned hits=0;
      void EINT2_IRQHandler(void) {hits++;}
      int main(void) {LPC_PINCON->PINSEL4=1<<24;LPC_SC->EXTMODE=0;
        NVIC_EnableIRQ(EINT2_IRQn);while(1) {}}''', [('CNB','CNB1')])
    m.run(10000)
    m.board.sw2=True
    m.observe()
    for _ in range(8):
        m.run(10000)
    assert m.irq_count>=3
    # This intentionally incomplete handler never clears EXTINT, so its
    # latched interrupt request must continue until firmware clears the flag.


def test_timer_mr1_interrupt_before_mr0_reset(compile_c):
    m=machine(compile_c, '''void TIMER0_IRQHandler(void) {
      if(LPC_TIM0->IR&2) LPC_GPIO0->FIOSET=0x10;LPC_TIM0->IR=255;}
      int main(void) {LPC_GPIO0->FIODIR=0x10;LPC_SC->PCONP|=2;
        LPC_TIM0->MR0=10;LPC_TIM0->MR1=8;LPC_TIM0->MCR=2|(1<<3);
        NVIC_EnableIRQ(TIMER0_IRQn);LPC_TIM0->TCR=1;while(1) {}}''', [('CNA','CNA1')])
    # Advance to the exact enable instruction, then inject a deterministic
    # elapsed clock interval crossing MR1 followed by MR0. Setup and handler
    # are still real firmware, not Python register writes.
    for _ in range(2000):
        m.run(1)
        if m.regs.get(0x40004004,0)&1:
            break
    assert m.regs.get(0x40004008,0)==0
    m._advance_timers(64)
    assert m.regs.get(0x40004000,0)&2
    for _ in range(8):
        m.run(10000)
    assert m.snapshot()['leds'][0]


def test_timer_stop_on_match_stops_at_match_count(compile_c):
    m=machine(compile_c, '''int main(void) {
      LPC_GPIO0->FIODIR=0xFF0;LPC_SC->PCONP|=2;
      LPC_TIM0->MR0=10;LPC_TIM0->MCR=5;LPC_TIM0->TCR=1;
      while(!(LPC_TIM0->IR&1));LPC_GPIO0->FIOPIN=LPC_TIM0->TC<<4;
      while(1) {}}''', [('CNA','CNA1')])
    for _ in range(2000):
        m.run(1)
        if m.regs.get(0x40004004,0)&1:
            break
    m._advance_timers(64)
    m.run(10000)
    assert m.gpio[0].latch & 0xFF0 == 10<<4
