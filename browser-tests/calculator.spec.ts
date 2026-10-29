import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

test('timer-delayed calculator reaches the LCD with F equals and E restart at the faster refresh cadence', async ({page, request}) => {
 const state = await (await request.get('/api/state')).json();
 await request.post('/api/control', {data:{action:'stop'}});
 for (const [header] of state.cables)
  await request.post('/api/physical', {data:{action:'disconnect', header}});
 await request.post('/api/physical', {data:{action:'release-inputs'}});
 await page.goto('/#ide');
 await page.getByLabel('Embedded C editor').fill(await readFile('examples/calculator_timer.c', 'utf8'));
 await page.getByRole('button', {name:'Compile C', exact:true}).click();
 await expect(page.getByText('C source · compiled', {exact:true})).toBeVisible();
 await page.getByRole('link', {name:'Board', exact:true}).click();
 for (const [a,b] of [['CND','CNAD'], ['CNB','CNB3']]) {
  await page.getByRole('button', {name:`Header ${a}`, exact:true}).click();
  await page.getByRole('button', {name:`Header ${b}`, exact:true}).click();
 }
 for (const [name,value] of [['JP5','closed'], ['JP16','closed'], ['JP4','1-2']])
  await page.getByLabel(`${name} position`).selectOption(value);
 const lcd = page.locator('g[aria-label^="LCD:"]');
 const started = performance.now();
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 await expect(lcd.locator('text').first()).toContainText('Enter A op B =');
 const startupMs = performance.now()-started;
 expect(startupMs).toBeLessThan(1500);
 const renderLatencies:number[] = [];
 async function press(character:string, expected:string) {
  const value = parseInt(character, 16);
  await page.getByRole('button', {name:`${character} SW${value+3} row ${Math.floor(value/4)+1} column ${value%4+1}`, exact:true}).focus();
  await page.keyboard.down('Space');
  // Firmware intentionally debounces and waits for release before reporting.
  await expect.poll(async () => (await (await request.get('/api/state')).json()).keys).toContain(value);
  await page.waitForTimeout(60);
  await page.keyboard.up('Space');
  await expect.poll(async () => (await (await request.get('/api/state')).json()).lcd[1].trimEnd(), {intervals:[10], timeout:1500}).toBe(expected);
  const backendReady = performance.now();
  await expect.poll(async () => (await lcd.locator('text').nth(1).textContent())?.trimEnd(), {intervals:[10], timeout:600}).toBe(expected);
  renderLatencies.push(performance.now()-backendReady);
 }
 for (const [a,op,b,answer] of [['3','A','4','3+4=7'], ['2','B','8','2-8=-6'], ['9','A','9','9+9=18']]) {
  const symbol = op==='A'?'+':'-';
  await press(a, a);
  await press(op, a+symbol);
  await press(b, a+symbol+b);
  await press('F', answer);
  await expect(lcd.locator('text').nth(1)).toContainText(answer);
  await page.screenshot({path:`test-results/calculator-${a}${op}${b}.png`, fullPage:true});
  await press('E', '');
  await expect(lcd.locator('text').first()).toContainText('Enter A op B =');
 }
 await writeFile('test-results/calculator-render-latency.json', JSON.stringify({startupMs, renderLatenciesMs:renderLatencies, maxRenderLatencyMs:Math.max(...renderLatencies)}, null, 2));
});
