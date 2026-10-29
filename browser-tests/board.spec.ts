import {test,expect} from '@playwright/test';

test('seven-segment and LED component numbers increase from right to left',async({page})=>{
 await page.goto('/#board');
 const board=page.getByLabel('Interactive ALS LPC1768 evaluation board',{exact:true});
 const display=page.getByLabel('Four-digit seven-segment display',{exact:true});
 await expect(display).toBeVisible();
 // Read physical screen positions, independently of the order of SVG elements.
 const digits=await display.locator(':scope > g').evaluateAll(elements=>elements
  .sort((a,b)=>a.getBoundingClientRect().x-b.getBoundingClientRect().x)
  .map(element=>element.getAttribute('aria-label')));
 expect(digits).toEqual(['U11','U10','U9','U8']);
 const leds=await board.locator('g[aria-label^="LD"]').filter({has:page.locator('ellipse')}).evaluateAll(elements=>elements
  .sort((a,b)=>a.getBoundingClientRect().x-b.getBoundingClientRect().x)
  .map(element=>element.querySelector('title')!.textContent));
 expect(leds).toEqual(['LD9','LD8','LD7','LD6','LD5','LD4','LD3','LD2']);
 const labels=await board.locator('text').evaluateAll(elements=>elements
  .filter(element=>/^(U(?:8|9|10|11)|LD[2-9])$/.test(element.textContent??''))
  .sort((a,b)=>a.getBoundingClientRect().x-b.getBoundingClientRect().x)
  .map(element=>element.textContent));
 expect(labels.filter(label=>label!.startsWith('U'))).toEqual(['U11','U10','U9','U8']);
 expect(labels.filter(label=>label!.startsWith('LD'))).toEqual(['LD9','LD8','LD7','LD6','LD5','LD4','LD3','LD2']);
});

test('the complete evaluation board renders as vectors without a photograph',async({page})=>{
 await page.goto('/');
 const board=page.getByLabel('Interactive ALS LPC1768 evaluation board',{exact:true});
 await expect(board).toBeVisible();
 await expect(board.locator('image')).toHaveCount(0);
 for(const name of ['UART0 AND UART3 INTERFACE','ETHERNET','ALPHANUMERIC LCD',
  '7 SEGMENT DISPLAY','POWER SUPPLY','RELAY CONTROL','DC MOTOR CONTROL',
  'STEPPER MOTOR CONTROL','USB HOST INTERFACE','USB DEVICE INTERFACE',
  'GENERAL PURPOSE LEDS','4X4 KEY MATRIX','CAN INTERFACE','RS485','I2C','SPI']){
  await expect(board.getByText(name,{exact:true})).toBeVisible();
 }
 for(const name of ['CNA','CNB','CNC','CND','CNA1','CNA2','CNB1','CNB2','CNB3','CNAD']){
  await expect(board.getByRole('button',{name:`Header ${name}`,exact:true})).toBeVisible();
 }
 await page.getByLabel('Board zoom').fill('140');
 await page.setViewportSize({width:430,height:932});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(430);
 await expect(board.getByRole('button',{name:'SW1 reset',exact:true})).toBeVisible();
});
