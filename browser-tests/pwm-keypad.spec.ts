import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('CND row-0 keys control PWM1.4 through the separate CNB cable', async ({page, request}) => {
 const errors:string[] = [];
 page.on('pageerror', error => errors.push(error.message));
 const previous = await (await request.get('/api/state')).json();
 await request.post('/api/control', {data:{action:'stop'}});
 for (const [header] of previous.cables)
  await request.post('/api/physical', {data:{action:'disconnect', header}});
 await request.post('/api/physical', {data:{action:'release-inputs'}});
 await page.goto('/#ide');
 await page.getByLabel('Embedded C editor').fill(await readFile('examples/pwm_keypad_timer.c', 'utf8'));
 await page.getByRole('button', {name:'Compile C', exact:true}).click();
 await expect(page.getByText('C source · compiled', {exact:true})).toBeVisible();
 await page.getByRole('link', {name:'Board', exact:true}).click();
 for (const [a,b] of [['CNB','CNB1'], ['CND','CNB3']]) {
  await page.getByRole('button', {name:`Header ${a}`, exact:true}).click();
  await page.getByRole('button', {name:`Header ${b}`, exact:true}).click();
 }
 await page.getByLabel('JP5 position').selectOption('closed');
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 await expect(page.getByLabel('LD10 PWM 10 percent', {exact:true})).toBeVisible();
 for (const [key,percent] of [[1,25], [2,50], [3,75], [0,10], [3,75]]) {
  await page.getByRole('button', {name:`${key} SW${key+3} row 1 column ${key+1}`, exact:true}).focus();
  await page.keyboard.down('Space');
  try {
   await expect(page.getByLabel(`LD10 PWM ${percent} percent`, {exact:true})).toBeVisible();
   expect((await (await request.get('/api/state')).json()).pwm).toBe(percent/100);
  } finally { await page.keyboard.up('Space'); }
  await expect.poll(async () => (await (await request.get('/api/state')).json()).keys).toEqual([]);
 }
 await expect(page.getByLabel('LD10 PWM 75 percent', {exact:true}).locator('circle').last()).toHaveAttribute('opacity', '0.75');
 expect(errors).toEqual([]);
 await page.screenshot({path:'test-results/pwm-keypad-live.png', fullPage:true});
});
