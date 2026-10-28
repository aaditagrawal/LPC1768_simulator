/* Row-0 keypad controls LD10: 0=10%, 1=25%, 2=50%, 3=75%.
 * Connect CNB -> CNB1 and CND -> CNB3. Close JP5 for column 4.
 * JP4 and JP18 are not used. Timer0 provides settling/debounce delays.
 */
#include <LPC17xx.h>

#define COLUMNS (0xFU << 23)
#define ROWS_P0 (3U << 27)
#define ROWS_P2 (3U << 0)

static void timing_init(void) {
    LPC_SC->PCONP |= 1U << 1;
    LPC_SC->PCLKSEL0 &= ~(3U << 2);
    LPC_TIM0->TCR = 2;
    LPC_TIM0->PR = SystemCoreClock / 4U / 1000000U - 1U;
    LPC_TIM0->MCR = 3;
    LPC_TIM0->IR = 0xFF;
}

static void delay_us(unsigned int us) {
    LPC_TIM0->TCR = 2;
    LPC_TIM0->MR0 = us;
    LPC_TIM0->IR = 1;
    LPC_TIM0->TCR = 1;
    while(!(LPC_TIM0->IR & 1U));
    LPC_TIM0->TCR = 0;
    LPC_TIM0->IR = 1;
}

void pwm_init(void) {
    SystemCoreClockUpdate();
    LPC_SC->PCONP |= 1U << 6;
    LPC_SC->PCLKSEL0 &= ~(3U << 12);
    LPC_PINCON->PINSEL3 &= ~(3U << 14);
    LPC_PINCON->PINSEL3 |= 2U << 14; /* P1.23 = PWM1.4. */
    LPC_PWM1->TCR = 2;
    LPC_PWM1->PR = SystemCoreClock / 4U / 1000000U - 1U;
    LPC_PWM1->MR0 = 1000;
    LPC_PWM1->MR4 = 100;
    LPC_PWM1->MCR = 1U << 1;
    LPC_PWM1->PCR = 1U << 12;
    LPC_PWM1->LER = (1U << 0) | (1U << 4);
    LPC_PWM1->TCR = 9;
}

void keypad_init(void) {
    LPC_PINCON->PINSEL1 &= ~(0xFFFU << 14);
    LPC_PINCON->PINSEL4 &= ~0xFU;
    /* CND pins 1-4 connect to CNB3 columns, not rows. */
    LPC_GPIO0->FIODIR &= ~COLUMNS;
    LPC_GPIO0->FIODIR |= ROWS_P0;
    LPC_GPIO2->FIODIR |= ROWS_P2;
    /* Disable MCU pulls on P0.23-P0.26; keypad has column pulldowns. */
    LPC_PINCON->PINMODE1 =
        (LPC_PINCON->PINMODE1 & ~(0xFFU << 14)) | (0xAAU << 14);
    LPC_GPIO0->FIOCLR = ROWS_P0;
    LPC_GPIO2->FIOCLR = ROWS_P2;
}

int readkey(void) {
    unsigned int col;
    LPC_GPIO0->FIOCLR = ROWS_P0;
    LPC_GPIO2->FIOCLR = ROWS_P2;
    LPC_GPIO0->FIOSET = 1U << 27; /* CND pin 5 = keypad row 0. */
    delay_us(10);
    col = (LPC_GPIO0->FIOPIN >> 23) & 0xFU;
    if(col & 1U) return 0;
    if(col & 2U) return 1;
    if(col & 4U) return 2;
    if(col & 8U) return 3;
    return -1;
}

int main(void) {
    static const unsigned int duty[4] = {100, 250, 500, 750};
    int key, last = -1;
    pwm_init();
    timing_init();
    keypad_init();
    while(1) {
        key = readkey();
        if(key >= 0 && last == -1) {
            delay_us(15000);
            if(readkey() == key) {
                LPC_PWM1->MR4 = duty[key];
                LPC_PWM1->LER = 1U << 4;
            }
        }
        last = key;
    }
}
