"""Compiled instructions, initialization, stack and optimization variants."""
import struct

import pytest

from simulator.compiler import Compiler
from simulator.engine import Machine


@pytest.mark.parametrize('optimization', [0, 1, 2, 3])
def test_compiler_optimizations_preserve_volatile_mmio_and_arm_arithmetic(optimization):
    source = '''#include <LPC17xx.h>
    volatile unsigned initialized=0x12345678; volatile unsigned zero;
    unsigned sum(unsigned n) {volatile unsigned local[4];
      local[0]=n;local[1]=n+1;local[2]=n+2;local[3]=n+3;
      return local[0]+local[1]+local[2]+local[3];}
    int main(void) {volatile unsigned *b=(void*)0x10007000;unsigned i;
      SystemCoreClockUpdate(); b[0]=initialized;b[1]=zero;b[2]=SystemCoreClock;
      b[3]=sum(0x7FFFFFFFu);b[4]=(0xFFFFFFFFu+1u);b[5]=(0x80000000u>>31);
      LPC_GPIO0->FIODIR=0xFF0;for(i=0;i<256;i++) LPC_GPIO0->FIOPIN=i<<4;
      b[6]=LPC_GPIO0->FIOSET;b[7]=0xC0DE;while(1) {}}
    '''
    m = Machine(Compiler(optimization=optimization).compile(source).hex)
    for _ in range(30):
        m.run(2000)
        values = struct.unpack('<8I', m.uc.mem_read(0x10007000, 32))
        if values[-1] == 0xC0DE:
            break
    assert values == (0x12345678, 0, 100000000, 2, 0, 1, 0xFF0, 0xC0DE)
    assert m.gpio_events == 256


@pytest.mark.parametrize('port,pin', [(0, 4), (1, 23), (2, 0), (3, 25), (4, 28)])
def test_gpio_open_drain_high_releases_pin_low_drives_pin(port, pin):
    from pathlib import Path
    m = Machine(Path('examples/idle.hex').read_text())
    base = 0x2009C000 + port * 32
    m.write_word(base, 1 << pin)
    m.write_word(base + 0x18, 1 << pin)
    assert m.pin_output(port, pin) == 1
    m.write_word(m.PIN + 0x68 + port * 4, 1 << pin)
    assert m.pin_output(port, pin) is None
    m.write_word(base + 0x1C, 1 << pin)
    assert m.pin_output(port, pin) == 0


def test_board_manual_three_megahertz_clock_profile_matches_cmsis():
    source = '''#include <LPC17xx.h>
    int main(void) {LPC_SC->PLL0CON=0;LPC_SC->CLKSRCSEL=1;LPC_SC->CCLKCFG=3;
      LPC_SC->PCLKSEL0=0x55555555;LPC_SC->PCLKSEL1=0x55555555;
      SystemCoreClockUpdate();*(volatile unsigned*)0x10007000=SystemCoreClock;
      while(1) {}}
    '''
    m = Machine(Compiler().compile(source).hex)
    m.run(10000)
    assert m.core_clock_hz() == 3000000
    assert struct.unpack('<I', m.uc.mem_read(0x10007000, 4))[0] == 3000000
    assert all(m.peripheral_clock_hz(base) == 3000000 for base in (*m.TIMERS, m.PWM))
