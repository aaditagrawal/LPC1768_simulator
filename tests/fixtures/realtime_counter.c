#include <LPC17xx.h>
#define SEG_MASK (0xFFU << 4)
#define DIG_MASK (0xFU << 23)
#define SW (1U << 0)
const unsigned char seg[10] = {
    0x3F, 0x06, 0x5B, 0x4F, 0x66,
    0x6D, 0x7D, 0x07, 0x7F, 0x6F
};
void init(void) {
    SystemCoreClockUpdate();
    LPC_PINCON->PINSEL0 &= ~(0xFFFFU << 8);
    LPC_GPIO0->FIODIR |= SEG_MASK;
    LPC_PINCON->PINSEL3 &= ~(0xFFU << 14);
    LPC_GPIO1->FIODIR |= DIG_MASK;
    LPC_PINCON->PINSEL4 &= ~3U;
    LPC_PINCON->PINMODE4 &= ~3U;
    LPC_GPIO2->FIODIR &= ~SW;
    LPC_SC->PCONP |= (1U << 1);
    LPC_SC->PCLKSEL0 &= ~(3U << 2);
    LPC_TIM0->TCR = 0x02;
    LPC_TIM0->PR = (SystemCoreClock / 4 / 1000) - 1;
    LPC_TIM0->MR0 = 1;
    LPC_TIM0->MCR = 0x03; // MR0 flag + reset on match
    LPC_TIM0->IR = 0xFF;
    LPC_TIM0->TCR = 0x01;
}
void wait1ms(void) {
    while(!(LPC_TIM0->IR & 1));
    LPC_TIM0->IR = 1;
}
void display_digit(unsigned int digit, unsigned int position) {
    LPC_GPIO1->FIOCLR = DIG_MASK;
    LPC_GPIO1->FIOSET = (4U << 23);
    LPC_GPIO0->FIOCLR = SEG_MASK;
    LPC_GPIO0->FIOSET = (seg[digit] << 4);
    LPC_GPIO1->FIOCLR = DIG_MASK;
    LPC_GPIO1->FIOSET = (position << 23);
}
int main(void) {
    unsigned int count = 0;
    unsigned int digits[4];
    unsigned int i;
    unsigned int ms = 0;
    unsigned int press_ms = 0;
    unsigned int release_ms = 0;
    int up = 1;
    int pressed = 0;
    init();
    while(1) {
        digits[0] = count / 1000;
        digits[1] = (count / 100) % 10;
        digits[2] = (count / 10) % 10;
        digits[3] = count % 10;
        for(i = 0; i < 4; i++) {
            display_digit(digits[i], i);
            wait1ms();
            ms++;
            if(!(LPC_GPIO2->FIOPIN & SW)) {
                release_ms = 0;
                if(!pressed) {
                    press_ms++;
                    if(press_ms >= 20) {
                        up = !up;
                        pressed = 1;
                    }
                }
            } else {
                press_ms = 0;
                if(pressed) {
                    release_ms++;
                    if(release_ms >= 20) {
                        pressed = 0;
                    }
                }
            }
            if(ms >= 1000) {
                ms = 0;
                if(up) count = (count + 1) % 10000;
                else count = (count + 9999) % 10000;
            }
        }
    }
}
