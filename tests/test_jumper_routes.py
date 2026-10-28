"""Manual JP4 selection must route P2.13 to only the selected header."""
from simulator.compiler import Compiler
from simulator.engine import Machine


def test_jp4_selects_cnc_pin9_without_connecting_it_in_other_positions():
    source='''#include <LPC17xx.h>
int main(void) {
 LPC_GPIO0->FIODIR=0x10;
 while(1) {
  if(LPC_GPIO2->FIOPIN & (1<<13)) LPC_GPIO0->FIOSET=0x10;
  else LPC_GPIO0->FIOCLR=0x10;
 }
}'''
    machine=Machine(Compiler().compile(source).hex)
    machine.board.connect('CNA','CNA1')
    machine.board.connect('CNC','CNB1')
    # Use the documented alternative SW2 profile to provide a driven input at pin 9.
    machine.board.sw2_pin=9
    machine.board.sw2=True
    for position,expected in [('1-2',True),('2-3',False),('open',True)]:
        machine.board.set_jumper('JP4',position)
        machine.run(10000)
        assert machine.snapshot()['leds'][0] is expected
