import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('a 1 ms multiplex scan counts wall-clock seconds, pauses, and reverses with SW2', async ({page, request}) => {
 const previous = await (await request.get('/api/state')).json();
 await request.post('/api/control', {data:{action:'stop'}});
 for (const [header] of previous.cables)
  await request.post('/api/physical', {data:{action:'disconnect', header}});
 await request.post('/api/physical', {data:{action:'release-inputs'}});
 await page.goto('/#ide');
 await page.getByLabel('Embedded C editor').fill(await readFile('tests/fixtures/realtime_counter.c', 'utf8'));
 await page.getByRole('button', {name:'Compile C', exact:true}).click();
 await expect(page.getByText('C source · compiled', {exact:true})).toBeVisible();
 await page.getByRole('link', {name:'Board', exact:true}).click();
 for (const [a,b] of [['CNA','CNA2'], ['CNB','CNB2'], ['CND','CNB1']]) {
  await page.getByRole('button', {name:`Header ${a}`, exact:true}).click();
  await page.getByRole('button', {name:`Header ${b}`, exact:true}).click();
 }
 const display = page.getByLabel('Four-digit seven-segment display', {exact:true});
 const bits = () => display.locator(':scope > g').evaluateAll(digits => digits.map(digit =>
  [...digit.querySelectorAll('polygon')].reduce((value, segment, i) =>
   value | (segment.getAttribute('fill')==='#ff4b36' ? 1<<i : 0), 0)));
 const started = performance.now();
 await page.getByRole('button', {name:'▶ Run', exact:true}).click();
 await expect.poll(bits, {intervals:[30], timeout:2000}).toEqual([63,63,63,6]);
 const first = (performance.now()-started)/1000;
 expect(first).toBeGreaterThan(.7);
 expect(first).toBeLessThan(1.8);
 await expect.poll(bits, {intervals:[30], timeout:1600}).toEqual([63,63,63,91]);
 await page.getByRole('button', {name:'Ⅱ Pause', exact:true}).click();
 const frozen = await (await request.get('/api/state')).json();
 // A fixed observation interval is intentional: paused time must be excluded.
 await page.waitForTimeout(1100);
 expect((await (await request.get('/api/state')).json()).elapsedSeconds).toBe(frozen.elapsedSeconds);
 await expect.poll(bits).toEqual([63,63,63,91]);
 await page.getByRole('button', {name:'▶ Resume', exact:true}).click();
 await expect.poll(bits, {intervals:[30], timeout:1600}).toEqual([63,63,63,79]);
 await page.getByRole('button', {name:'SW2', exact:true}).focus();
 await page.keyboard.down('Space');
 await page.waitForTimeout(120);
 await page.keyboard.up('Space');
 await expect.poll(bits, {intervals:[30], timeout:1600}).toEqual([63,63,63,91]);
 await page.screenshot({path:'test-results/realtime-counter.png', fullPage:true});
});
