"""Generate separate corrected firmware examples; no simulation logic lives here."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'examples'
OUT.mkdir(exist_ok=True)

COMMON = r'''/* Corrected lab reference. See docs/BOARD_NOTES.md; original PDFs are unchanged. */
#include <LPC17xx.h>

void delay(unsigned n) { volatile unsigned i; for(i=0;i<n;i++); }
void setup(void) { SystemInit(); SystemCoreClockUpdate(); }
void leds_init(void) { LPC_PINCON->PINSEL0 &= 0xFF0000FF; LPC_GPIO0->FIODIR |= 0xFF0; }
void leds(unsigned v) { LPC_GPIO0->FIOCLR=0xFF0; LPC_GPIO0->FIOSET=(v&255)<<4; }
unsigned switch_up(void) { return (LPC_GPIO2->FIOPIN >> 12)&1; }
void lcd_nibble(unsigned v,unsigned rs) {
  LPC_GPIO0->FIOPIN=(v<<23)|(rs<<27);
  LPC_GPIO0->FIOSET=1<<28; delay(4); LPC_GPIO0->FIOCLR=1<<28;
}
void lcd_byte(unsigned v,unsigned rs) { lcd_nibble(v>>4,rs); lcd_nibble(v&15,rs); }
void lcd_init(void) {
  LPC_PINCON->PINSEL1 &= ~0x03FFC000;
  LPC_GPIO0->FIODIR |= 0x1F800000;
  lcd_nibble(3,0); lcd_nibble(3,0); lcd_nibble(3,0); lcd_nibble(2,0);
  lcd_byte(0x28,0); lcd_byte(0x0C,0); lcd_byte(0x06,0); lcd_byte(1,0);
}
void lcd_text(const char *s) { while(*s) lcd_byte(*s++,1); }
void lcd_at(unsigned addr) { lcd_byte(0x80|addr,0); }
void lcd_number(int number) {
  char digits[12]; unsigned i=0,n;
  if(number<0) {lcd_byte('-',1); n=(unsigned)(-number);} else n=(unsigned)number;
  do { digits[i++]=(char)('0'+n%10); n/=10; } while(n);
  while(i) lcd_byte(digits[--i],1);
}
void keypad_init(void) {
  LPC_PINCON->PINSEL3 &= 0xFFC03FFF;
  LPC_PINCON->PINSEL4 &= 0xF00FFFFF;
  LPC_GPIO2->FIODIR |= 0x3C00; LPC_GPIO1->FIODIR &= ~0x07800000;
}
int keypad_read(void) {
  unsigned row,col,bits;
  for(row=0;row<4;row++) {
    LPC_GPIO2->FIOCLR=0x3C00; LPC_GPIO2->FIOSET=1<<(10+row);
    bits=(LPC_GPIO1->FIOPIN>>23)&15;
    for(col=0;col<4;col++) if(bits&(1<<col)) return (int)(row*4+col);
  } return -1;
}
const unsigned patterns[16]={0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,
  0x7F,0x6F,0x77,0x7C,0x39,0x5E,0x79,0x71};
void seg_init(void) {
  leds_init(); LPC_PINCON->PINSEL3 &= 0xFFC03FFF; LPC_GPIO1->FIODIR |= 0x07800000;
}
void seg_scan(unsigned value,unsigned radix) {
  unsigned d;
  for(d=0;d<4;d++) {
    LPC_GPIO1->FIOPIN=d<<23; LPC_GPIO0->FIOPIN=patterns[value%radix]<<4;
    delay(40); LPC_GPIO0->FIOCLR=0xFF0; LPC_GPIO1->FIOPIN=5<<23;
    value/=radix;
  }
}
void timer_init(void) {
  LPC_SC->PCONP |= 2; LPC_TIM0->TCR=2; LPC_TIM0->PR=99;
  LPC_TIM0->MR0=1000; LPC_TIM0->MCR=3; LPC_TIM0->TCR=1;
}
unsigned timer_elapsed(void) { if(LPC_TIM0->IR&1) {LPC_TIM0->IR=1; return 1;} return 0; }
void adc_init(void) {
  LPC_SC->PCONP |= 1<<12; LPC_PINCON->PINSEL3 |= 0xF0000000;
  LPC_PINCON->PINMODE3=(LPC_PINCON->PINMODE3&~0xF0000000u)|0xA0000000u;
}
unsigned adc_read(unsigned channel) {
  unsigned v; LPC_ADC->ADCR=(1<<channel)|(1u<<8)|(1<<21)|(1<<24);
  do {v=LPC_ADC->ADGDR;} while(!(v&(1u<<31))); return (v>>4)&4095;
}
'''

SPECS = []

def add(id, lab, title, body, cables, jumpers=None, description=''):
    (OUT / f'{id}.c').write_text(COMMON + '\n' + body + '\n', encoding='utf-8')
    SPECS.append(dict(id=id,lab=lab,title=title,file=f'{id}.c',cables=cables,
                      jumpers=jumpers or {},description=description,status='working'))

LED = [['CNA','CNA1']]
SW = LED + [['CNB','CNB1']]
SEG = [['CNA','CNA2'],['CNB','CNB2']]
LCD = [['CND','CNAD']]
LCD_J = {'JP5':'closed','JP16':'closed'}
KEY_J = {**LCD_J,'JP4':'1-2'}

add('lab6_blink',6,'Blink LD2–LD9',r'''int main(void) {setup(); leds_init();
 while(1) {leds(255); delay(10000); leds(0); delay(10000);} }''',LED,
 description='Active-high outputs on P0.4–P0.11. Observe all eight LEDs blink.')
add('lab6_switch',6,'SW2 controls LD2',r'''int main(void) {setup(); leds_init();
 while(1) leds(switch_up()?0:1); }''',SW,
 description='Poll P2.12. Press SW2 to illuminate LD2; release to turn it off.')
add('lab7_sequence',7,'Serial LED ON / OFF',r'''int main(void) {unsigned bit;setup();leds_init();
 while(1) {for(bit=0;bit<8;bit++) {LPC_GPIO0->FIOSET=1<<(4+bit);delay(10000);}
 for(bit=0;bit<8;bit++) {LPC_GPIO0->FIOCLR=1<<(4+bit);delay(10000);}} }''',LED,
 description='Corrected Lab 7 sample: illuminate each LED in sequence, then clear each in sequence.')
add('lab7_binary',7,'8-bit binary up counter',r'''int main(void) {unsigned v=0;setup();leds_init();
 while(1) {leds(v++);delay(10000);} }''',LED)
add('lab7_updown',7,'SW2 up / down counter',r'''int main(void) {unsigned v=0;setup();leds_init();
 while(1) {leds(v);v+=switch_up()?1:-1;delay(10000);} }''',SW,
 description='Released SW2 counts up; pressed SW2 counts down. Wraps at eight bits.')
add('lab7_ring',7,'SW2 ring counter',r'''int main(void) {unsigned v=1,old=1,s;setup();leds_init();leds(v);
 while(1) {s=switch_up();if(old&&!s) {v=((v<<1)|(v>>7))&255;leds(v);} old=s;} }''',SW)
add('lab8_bcd_up',8,'Four-digit BCD up counter',r'''int main(void) {unsigned v=0,n=0;setup();seg_init();
 while(1) {seg_scan(v,10);if(++n==20) {n=0;v=(v+1)%10000;}} }''',SEG,
 description='U7 uses a BCD digit address. Four displays are reconstructed from every GPIO transition.')
add('lab8_bcd_updown',8,'BCD up / down with timer',r'''int main(void) {unsigned v=0;setup();seg_init();timer_init();
 while(1) {seg_scan(v,10);if(timer_elapsed()) v=(v+(switch_up()?1:9999))%10000;} }''',SEG,
 description='Timer0 controls increments. CNB is occupied by CNB2: SW2 may instead connect CNC→CNB1, requiring firmware to poll P0.21.')
# A dedicated alternate header preserves one cable per header for switch + display.
p = OUT / 'lab8_bcd_updown.c'
p.write_text(p.read_text().replace('v+(switch_up()?1:9999)', 'v+((LPC_GPIO0->FIOPIN&(1<<21))?1:9999)'), encoding='utf-8')
SPECS[-1]['cables'] = SEG + [['CNC','CNB1']]
add('lab8_ring',8,'Four-digit binary ring counter',r'''int main(void) {unsigned v=1,n=0,d;setup();seg_init();
 while(1) {for(d=0;d<4;d++) {LPC_GPIO1->FIOPIN=d<<23;
 LPC_GPIO0->FIOPIN=((v>>(d*4))&15)<<4;delay(40);
 LPC_GPIO0->FIOCLR=0xFF0;LPC_GPIO1->FIOPIN=5<<23;}
 if(++n==20) {n=0;v=((v<<1)|(v>>15))&65535;}} }''',SEG)
add('lab8_bcd_down',8,'Four-digit BCD down counter',r'''int main(void) {unsigned v=9999;setup();seg_init();timer_init();
 while(1) {seg_scan(v,10);if(timer_elapsed()) v=(v+9999)%10000;} }''',SEG)
add('lab8_hex_updown',8,'Hexadecimal up / down counter',r'''int main(void) {unsigned v=0;setup();seg_init();timer_init();
 while(1) {seg_scan(v,16);if(timer_elapsed()) v=(v+((LPC_GPIO0->FIOPIN&(1<<21))?1:-1))&65535;} }''',SEG+[['CNC','CNB1']],
 description='CNC→CNB1 routes SW2 pin 7 to P0.21 while CNB is used for digit selection.')
add('lab9_message',9,'LCD message',r'''int main(void) {setup();lcd_init();lcd_text("MIT Manipal");
 lcd_at(0x40);lcd_text("LPC1768 Lab");while(1) {} }''',LCD,LCD_J)
add('lab9_dice',9,'SW2 dice',r'''volatile unsigned roll=0,dice_value=0,dice_pending=0;
void EINT2_IRQHandler(void) {
  LPC_SC->EXTINT=4;
  dice_value=roll; /* ESD PDF p41 specifies 0 through 6. */
  dice_pending=1;
}
int main(void) {setup();lcd_init();lcd_text("Press SW2");
  LPC_PINCON->PINSEL4=(LPC_PINCON->PINSEL4&~(3u<<24))|(1u<<24);
  LPC_SC->EXTMODE |= 4; LPC_SC->EXTPOLAR &= ~4u; LPC_SC->EXTINT=4;
  NVIC_EnableIRQ(EINT2_IRQn);
  while(1) {
    roll=(roll+1)%7;
    if(dice_pending) {
      dice_pending=0;lcd_at(0x40);lcd_text("Dice: ");lcd_number(dice_value);
    }
  }
}''',LCD+[['CNB','CNB1']],LCD_J)
add('lab9_keypad',9,'Keypad keycode on LCD',r'''int main(void) {int key,old=-1;setup();lcd_init();keypad_init();lcd_text("Keycode 0-F");
 while(1) {key=keypad_read();if(key>=0&&key!=old) {lcd_at(0x40);lcd_text("Key: ");lcd_byte("0123456789ABCDEF"[key],1);} old=key;} }''',LCD+[['CNB','CNB3']],KEY_J)
add('lab9_calculator',9,'Single-digit + / − calculator',r'''int main(void) {int key,old=-1,a=0,b=0,op=0,stage=0;setup();lcd_init();keypad_init();
 lcd_text("A:+ B:- E:= F:C");lcd_at(0x40);
 while(1) {key=keypad_read();if(key>=0&&key!=old) {
 if(key==15) {stage=0;lcd_at(0x40);lcd_text("                ");lcd_at(0x40);}
 else if(key<10&&stage==0) {a=key;stage=1;lcd_number(a);}
 else if((key==10||key==11)&&stage==1) {op=key;stage=2;lcd_byte(key==10?'+':'-',1);}
 else if(key<10&&stage==2) {b=key;stage=3;lcd_number(b);}
 else if(key==14&&stage==3) {lcd_byte('=',1);lcd_number(op==10?a+b:a-b);stage=4;}
 } old=key;} }''',LCD+[['CNB','CNB3']],KEY_J,
 description='Use row-major keycodes: A adds, B subtracts, E equals, F clears. Operands are 0–9.')
add('lab10_adc5',10,'POT1 / ADC0.5 on LCD',r'''int main(void) {unsigned raw,mv;setup();lcd_init();adc_init();lcd_text("AD0.5 POT1");
 while(1) {raw=adc_read(5);mv=raw*3300/4095;lcd_at(0x40);lcd_text("                ");lcd_at(0x40);
 lcd_number(raw);lcd_text(" ");lcd_number(mv/1000);lcd_byte('.',1);
 lcd_byte('0'+(mv/100)%10,1);lcd_byte('0'+(mv/10)%10,1);lcd_byte('0'+mv%10,1);lcd_byte('V',1);delay(4000);} }''',LCD,LCD_J)
add('lab10_difference',10,'POT4 − POT1 voltage difference',r'''int main(void) {int a,b,d;setup();lcd_init();adc_init();lcd_text("POT4 minus POT1");
 while(1) {a=adc_read(4);b=adc_read(5);d=a-b;
 lcd_at(0x40);lcd_text("                ");lcd_at(0x40);lcd_number(d);lcd_text(" counts");delay(4000);} }''',LCD,{**LCD_J,'JP18':'2-3'},
 description='Displays the signed difference of 12-bit ADC readings. JP18 2–3 connects POT4 to AD0.4.')
add('lab11_pwm',11,'PWM1.4 brightness sweep',r'''volatile unsigned rising=1;
void PWM1_IRQHandler(void) {LPC_PWM1->IR=255;
 if(rising) {LPC_PWM1->MR4+=100;if(LPC_PWM1->MR4>=27000) rising=0;}
 else {LPC_PWM1->MR4-=100;if(LPC_PWM1->MR4<=0x500) rising=1;}
 LPC_PWM1->LER=0x11;}
int main(void) {setup();LPC_SC->PCONP|=1<<6;LPC_PINCON->PINSEL3=(LPC_PINCON->PINSEL3&~(3<<14))|(2<<14);
 LPC_PWM1->PCR=1<<12;LPC_PWM1->MCR=3;LPC_PWM1->MR0=30000;LPC_PWM1->MR4=0x500;
 LPC_PWM1->LER=0x11;LPC_PWM1->TCR=2;LPC_PWM1->TCR=9;NVIC_EnableIRQ(PWM1_IRQn);while(1) {} }''',[['CNB','CNB1']],
 description='Actual PWM interrupt handler changes MR4. LD10 brightness follows latched MR4 / MR0.')

# Lab 8 timer exercises require one-second hardware-timer intervals. Keep the
# unused common helper unchanged in other references to avoid unrelated rewrites.
ONE_SECOND_TIMER = r'''void timer_init(void) {
  SystemCoreClockUpdate();
  LPC_SC->PCONP |= 2;
  LPC_SC->PCLKSEL0 &= ~(3u << 2); /* Timer0 PCLK = CCLK / 4. */
  LPC_TIM0->TCR=2;
  LPC_TIM0->PR=SystemCoreClock / 4u / 1000u - 1u;
  LPC_TIM0->MR0=1000; LPC_TIM0->MCR=3;
  LPC_TIM0->IR=255; LPC_TIM0->TCR=1; /* One match each second. */
}'''
for timer_example in ('lab8_bcd_updown', 'lab8_hex_updown', 'lab8_bcd_down'):
    timer_path = OUT / f'{timer_example}.c'
    timer_source = timer_path.read_text(encoding='utf-8')
    old_timer = COMMON[COMMON.index('void timer_init(void) {'):COMMON.index('unsigned timer_elapsed(void)')]
    timer_path.write_text(timer_source.replace(old_timer, ONE_SECOND_TIMER + '\n'), encoding='utf-8')

(OUT / 'catalog.json').write_text(json.dumps(SPECS,indent=2,ensure_ascii=False), encoding='utf-8')
print(f'Generated {len(SPECS)} corrected standalone C reference programs.')
