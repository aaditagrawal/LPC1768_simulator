/* Standalone calculator: A adds, B subtracts, F equals, E restarts.
 * CND -> CNAD, CNB -> CNB3; JP5/JP16 closed and JP4 at 1-2.
 * Timer0 provides delays; no 50000-iteration software waits are required.
 */
#include <LPC17xx.h>

#define RS       (1U << 27)
#define EN       (1U << 28)
#define LCD_DATA (0xFU << 23)
#define ROWS     (0xFU << 10)
#define COLS     (0xFU << 23)

static void timer_init(void) {
    SystemCoreClockUpdate();
    LPC_SC->PCONP |= 1U << 1;
    LPC_SC->PCLKSEL0 &= ~(3U << 2); /* Timer0 clock = CCLK / 4. */
    LPC_TIM0->TCR = 2;
    LPC_TIM0->PR = SystemCoreClock / 4U / 1000000U - 1U;
    LPC_TIM0->MCR = 3;             /* Set MR0 flag and reset on match. */
    LPC_TIM0->IR = 0xFF;
}

static void delay_us(unsigned int us) {
    if(!us) return;
    LPC_TIM0->TCR = 2;
    LPC_TIM0->MR0 = us;
    LPC_TIM0->IR = 1;
    LPC_TIM0->TCR = 1;
    while(!(LPC_TIM0->IR & 1U));
    LPC_TIM0->TCR = 0;
    LPC_TIM0->IR = 1;
}

static void delay_ms(unsigned int ms) {
    delay_us(ms * 1000U);
}

void lcd_nibble(unsigned int x) {
    LPC_GPIO0->FIOCLR = LCD_DATA;
    LPC_GPIO0->FIOSET = (x & 0xFU) << 23;
    LPC_GPIO0->FIOSET = EN;
    delay_us(1);
    LPC_GPIO0->FIOCLR = EN;
    delay_us(50);
}

void lcd_cmd(unsigned int cmd) {
    LPC_GPIO0->FIOCLR = RS;
    lcd_nibble(cmd >> 4);
    lcd_nibble(cmd);
    if(cmd == 0x01 || cmd == 0x02) delay_ms(2);
}

void lcd_data(char ch) {
    LPC_GPIO0->FIOSET = RS;
    lcd_nibble((unsigned char)ch >> 4);
    lcd_nibble((unsigned char)ch);
}

void lcd_string(const char *s) {
    while(*s) lcd_data(*s++);
}

void lcd_init(void) {
    LPC_PINCON->PINSEL1 &= ~(0xFFFU << 14);
    LPC_GPIO0->FIODIR |= LCD_DATA | RS | EN;
    LPC_GPIO0->FIOCLR = LCD_DATA | RS | EN;
    delay_ms(40);
    lcd_nibble(3); delay_ms(5);
    lcd_nibble(3); delay_ms(1);
    lcd_nibble(3); delay_ms(1);
    lcd_nibble(2); delay_ms(1);
    lcd_cmd(0x28);
    lcd_cmd(0x0C);
    lcd_cmd(0x06);
    lcd_cmd(0x01);
}

void keypad_init(void) {
    LPC_PINCON->PINSEL3 &= ~(0xFFU << 14);
    LPC_PINCON->PINSEL4 &= ~(0xFFU << 20);
    LPC_GPIO2->FIODIR |= ROWS;    /* P2.10-P2.13 drive rows. */
    LPC_GPIO1->FIODIR &= ~COLS;   /* P1.23-P1.26 read columns. */
    LPC_GPIO2->FIOCLR = ROWS;
}

char getkey(void) {
    static const char keys[4][4] = {
        {'0','1','2','3'}, {'4','5','6','7'},
        {'8','9','A','B'}, {'C','D','E','F'}
    };
    unsigned int row, col, value;
    for(row = 0; row < 4; row++) {
        LPC_GPIO2->FIOCLR = ROWS;
        LPC_GPIO2->FIOSET = 1U << (10 + row);
        delay_ms(1);
        value = (LPC_GPIO1->FIOPIN >> 23) & 0xFU;
        for(col = 0; col < 4; col++) {
            if(value & (1U << col)) {
                delay_ms(15);
                if(LPC_GPIO1->FIOPIN & (1U << (23 + col))) {
                    /* Keep the scanned row driven until this key is released. */
                    while(LPC_GPIO1->FIOPIN & (1U << (23 + col)));
                    delay_ms(10);
                    LPC_GPIO2->FIOCLR = ROWS;
                    return keys[row][col];
                }
            }
        }
    }
    LPC_GPIO2->FIOCLR = ROWS;
    return 0;
}

char readkey(void) {
    char key = 0;
    while(key == 0) key = getkey();
    return key;
}

void display_result(int result) {
    if(result < 0) {
        lcd_data('-');
        result = -result;
    }
    if(result >= 10) lcd_data((char)('0' + result / 10));
    lcd_data((char)('0' + result % 10));
}

int main(void) {
    char key, op;
    int A, B, result;
    timer_init();
    lcd_init();
    keypad_init();
    while(1) {
        lcd_cmd(0x01);
        lcd_string("Enter A op B =");
        lcd_cmd(0xC0);
        do { key = readkey(); } while(key < '0' || key > '9');
        A = key - '0';
        lcd_data(key);
        do { key = readkey(); } while(key != 'A' && key != 'B');
        op = key == 'A' ? '+' : '-';
        lcd_data(op);
        do { key = readkey(); } while(key < '0' || key > '9');
        B = key - '0';
        lcd_data(key);
        do { key = readkey(); } while(key != 'F');
        lcd_data('=');
        result = op == '+' ? A + B : A - B;
        display_result(result);
        do { key = readkey(); } while(key != 'E');
    }
}
