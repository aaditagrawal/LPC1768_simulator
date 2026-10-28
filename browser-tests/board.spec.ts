import {test,expect} from '@playwright/test';

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
