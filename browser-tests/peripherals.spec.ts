import {test, expect, type Page} from '@playwright/test';

async function compile(page:Page, source:string) {
 await page.goto('/#ide');
 await page.getByLabel('Embedded C editor').fill(source);
 await page.getByRole('button', {name:'Compile C', exact:true}).click();
 await expect(page.getByText('C source · compiled', {exact:true})).toBeVisible();
 await page.getByRole('link', {name:'Board', exact:true}).click();
}

test.beforeEach(async ({request}) => {
 const state = await (await request.get('/api/state')).json();
 await request.post('/api/control', {data:{action:'stop'}});
 for (const [header] of state.cables) await request.post('/api/physical', {data:{action:'disconnect', header}});
 for (const name of Object.keys(state.jumpers)) await request.post('/api/physical', {data:{action:'jumper', name, value:'open'}});
 await request.post('/api/physical', {data:{action:'release-inputs'}});
});

test('all sixteen physical keypad buttons reach the LCD with manual jumper routing', async ({page, request}) => {
 const {source} = await (await request.get('/api/examples/lab9_keypad')).json();
 await compile(page, source);
 for (const [a,b] of [['CND','CNAD'], ['CNB','CNB3']]) {
  await page.getByRole('button', {name:`Header ${a}`, exact:true}).click();
  await page.getByRole('button', {name:`Header ${b}`, exact:true}).click();
 }
 for (const [name,value] of [['JP4','1-2'], ['JP5','closed'], ['JP16','closed']])
  await page.getByLabel(`${name} position`).selectOption(value);
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 const lcd = page.locator('g[aria-label^="LCD:"]');
 await expect(lcd.locator('text').first()).toHaveText('Keycode 0-F     ');
 for (let key=0; key<16; key++) {
  const character = key.toString(16).toUpperCase();
  const button = page.getByRole('button', {name:`${character} SW${key+3} row ${Math.floor(key/4)+1} column ${key%4+1}`, exact:true});
  await button.focus();
  await page.keyboard.down('Space');
  try { await expect(lcd.locator('text').nth(1)).toHaveText(`Key: ${character}`.padEnd(16)); }
  finally { await page.keyboard.up('Space'); }
  await expect.poll(async () => (await (await request.get('/api/state')).json()).keys).toEqual([]);
 }
 await page.screenshot({path:'test-results/peripheral-keypad-lcd.png', fullPage:true});
});

test('POT1 slider drives ADC text and opening the LCD jumper hides both text lines', async ({page, request}) => {
 const {source} = await (await request.get('/api/examples/lab10_adc5')).json();
 await compile(page, source);
 await page.getByRole('button', {name:'Header CND', exact:true}).click();
 await page.getByRole('button', {name:'Header CNAD', exact:true}).click();
 await page.getByLabel('JP5 position').selectOption('closed');
 await page.getByLabel('JP16 position').selectOption('closed');
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 const lines = page.locator('g[aria-label^="LCD:"] text');
 for (const [voltage,text] of [['3.3','4095 3.300V'], ['0','0 0.000V']]) {
  await page.getByLabel('POT1 voltage').fill(voltage);
  await expect(lines.nth(1)).toContainText(text);
 }
 await page.screenshot({path:'test-results/peripheral-adc-lcd.png', fullPage:true});
 await page.getByLabel('JP16 position').selectOption('open');
 await expect(lines).toHaveCount(0);
 const difference = await (await request.get('/api/examples/lab10_difference')).json();
 await compile(page, difference.source);
 await page.getByLabel('JP16 position').selectOption('closed');
 await page.getByLabel('JP18 position').selectOption('2-3');
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 await page.getByLabel('POT4 voltage').fill('3.3');
 await page.getByLabel('POT1 voltage').fill('0');
 await expect(lines.nth(1)).toContainText('4095 counts');
 for (const position of ['open', '1-2']) {
  await page.getByLabel('JP18 position').selectOption(position);
  await expect(lines.nth(1)).toContainText('0 counts');
 }
 await page.getByLabel('JP18 position').selectOption('2-3');
 await expect(lines.nth(1)).toContainText('4095 counts');
 await page.getByLabel('POT4 voltage').fill('0');
 await page.getByLabel('POT1 voltage').fill('3.3');
 await expect(lines.nth(1)).toContainText('-4095 counts');
});

test('firmware segment bits and PWM duty reach the drawn displays and respect cable removal', async ({page, request}) => {
 const source = `#include <LPC17xx.h>
 int main(void) {unsigned d; volatile unsigned wait;
 const unsigned patterns[4]={0x06,0x5B,0x4F,0x66};
 LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO1->FIODIR=0x07800000;
 while(1) {for(d=0;d<4;d++) {LPC_GPIO1->FIOPIN=d<<23;
 LPC_GPIO0->FIOPIN=patterns[d]<<4;for(wait=0;wait<30;wait++);
 LPC_GPIO0->FIOCLR=0xFF0;LPC_GPIO1->FIOPIN=5<<23;}}}`;
 await compile(page, source);
 for (const [a,b] of [['CNA','CNA2'], ['CNB','CNB2']])
  await request.post('/api/physical', {data:{action:'connect', a, b}});
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 const display = page.getByLabel('Four-digit seven-segment display', {exact:true});
 const visibleBits = () => display.locator(':scope > g').evaluateAll(digits => digits.map(digit =>
  [...digit.querySelectorAll('polygon')].reduce((bits, segment, i) => bits | (segment.getAttribute('fill')==='#ff4b36' ? 1<<i : 0), 0)));
 await expect.poll(visibleBits).toEqual([0x06,0x5B,0x4F,0x66]);
 await page.screenshot({path:'test-results/peripheral-seven-segment.png', fullPage:true});
 await request.post('/api/physical', {data:{action:'disconnect', header:'CNA'}});
 await expect.poll(visibleBits).toEqual([0,0,0,0]);
 await request.post('/api/control', {data:{action:'stop'}});
 await request.post('/api/physical', {data:{action:'disconnect', header:'CNB'}});
 const pwmSource = `#include <LPC17xx.h>
 int main(void) {LPC_SC->PCONP|=1<<6;LPC_PINCON->PINSEL3=2<<14;
 LPC_PWM1->MR0=1000;LPC_PWM1->MR4=250;LPC_PWM1->MCR=2;LPC_PWM1->PCR=1<<12;
 LPC_PWM1->LER=0x11;LPC_PWM1->TCR=9;while(1) {}}`;
 await compile(page, pwmSource);
 await request.post('/api/physical', {data:{action:'connect', a:'CNB', b:'CNB1'}});
 await request.post('/api/control', {data:{action:'run'}});
 await expect(page.getByLabel('LD10 PWM 25 percent', {exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/peripheral-pwm.png', fullPage:true});
 await request.post('/api/physical', {data:{action:'disconnect', header:'CNB'}});
 await expect(page.getByLabel('LD10 PWM 0 percent', {exact:true})).toBeVisible();
});
