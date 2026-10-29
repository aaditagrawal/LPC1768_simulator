import {test,expect} from '@playwright/test';

test.beforeEach(async({page,request})=>{
 const s=await (await request.get('/api/state')).json();
 await request.post('/api/control',{data:{action:'stop'}});
 for(const cable of s.cables)await request.post('/api/physical',{data:{action:'disconnect',header:cable[0]}});
 for(const name of Object.keys(s.jumpers))await request.post('/api/physical',{data:{action:'jumper',name,value:'open'}});
 await request.post('/api/physical',{data:{action:'release-inputs'}});
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Virtual evaluation board'})).toBeVisible();
});

test('manual cable, real C compile, LEDs, cable removal and controls',async({page,request})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await page.getByLabel('Embedded C editor').fill(`#include <LPC17xx.h>
 int main(void) {SystemInit();SystemCoreClockUpdate();LPC_GPIO0->FIODIR=0xFF0;
 LPC_GPIO0->FIOSET=0xA50;while(1) {}}`);
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await expect(page.getByRole('button',{name:'▶ Run',exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('link',{name:'Board',exact:true}).click();
 await page.getByRole('button',{name:'Header CNA',exact:true}).click();
 await page.getByRole('button',{name:'Header CNA1',exact:true}).click();
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).cables).toEqual([['CNA','CNA1']]);
 await page.getByRole('button',{name:'▶ Run',exact:true}).click();
 await expect(page.getByLabel('LD2 on',{exact:true})).toBeVisible();
 await expect(page.getByLabel('LD9 on',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Ⅱ Pause',exact:true}).click();
 await expect(page.getByRole('button',{name:'▶ Resume',exact:true})).toBeEnabled();
 const ticks=(await (await request.get('/api/state')).json()).ticks;
 await page.waitForTimeout(300);
 expect((await (await request.get('/api/state')).json()).ticks).toBe(ticks);
 const point=await page.getByRole('button',{name:'Disconnect CNA to CNA1',exact:true}).locator('path').last().evaluate((p:SVGPathElement)=>{
  const mid=p.getPointAtLength(p.getTotalLength()/2).matrixTransform(p.getScreenCTM()!);
  return {x:mid.x,y:mid.y};
 });
 await page.mouse.click(point.x,point.y);
 await expect(page.getByLabel('LD2 off',{exact:true})).toBeVisible();
 const s=await (await request.get('/api/state')).json();
 expect(s.gpio[0].latch).toBe('0x00000A50');
 await page.getByRole('button',{name:'↺ Reset',exact:true}).click();
 expect((await (await request.get('/api/state')).json()).ticks).toBe(0);
 await page.screenshot({path:'test-results/board-desktop.png',fullPage:true});
 expect(errors).toEqual([]);
});

test('exercise selection preserves source and never configures hardware',async({page,request})=>{
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await page.getByLabel('Embedded C editor').fill('int main(void) { while(1) {} }');
 await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await page.getByRole('button',{name:'Keypad keycode on LCD',exact:true}).click();
 expect((await (await request.get('/api/state')).json()).cables).toEqual([]);
 await page.getByRole('link',{name:'Board',exact:true}).click();
 await page.getByLabel('JP4 position').selectOption('1-2');
 await page.getByRole('button',{name:'Jumper JP5 open',exact:true}).click();
 await expect(page.getByLabel('JP5 position')).toHaveValue('closed');
 await page.getByLabel('JP16 position').selectOption('closed');
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await expect(page.getByLabel('Embedded C editor')).toHaveValue('int main(void) { while(1) {} }');
 await expect(page.getByText('Keypad keycode on LCD',{exact:true})).toBeVisible();
 const s=await (await request.get('/api/state')).json();
 expect(s.cables).toEqual([]);
 expect(s.jumpers.JP4).toBe('1-2');
});

test('HEX upload and real LCD firmware through manual wiring',async({page,request})=>{
 const source=await (await request.get('/api/examples/lab9_message')).json();
 const result=await (await request.post('/api/compile',{data:{source:source.source}})).json();
 expect(result.hex).toContain(':00000001FF');
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await page.getByLabel('Upload C or HEX').setInputFiles({name:'lcd.hex',mimeType:'text/plain',buffer:Buffer.from(result.hex)});
 await expect(page.getByText('HEX firmware loaded',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Board',exact:true}).click();
 await page.getByRole('button',{name:'Header CND',exact:true}).click();
 await page.getByRole('button',{name:'Header CNAD',exact:true}).click();
 await page.getByLabel('JP5 position').selectOption('closed');
 await page.getByLabel('JP16 position').selectOption('closed');
 await page.getByRole('button',{name:'▶ Run',exact:true}).click();
 await expect(page.getByLabel(/^LCD: MIT Manipal/)).toBeVisible();
 await page.getByLabel('JP16 position').selectOption('open');
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).lcd).toEqual([' '.repeat(16),' '.repeat(16)]);
 await page.screenshot({path:'test-results/lcd-firmware.png',fullPage:true});
});

test('momentary SW2 and keypad release; responsive viewport',async({page,request})=>{
 const sw=page.getByRole('button',{name:'SW2',exact:true});
 await sw.focus();await page.keyboard.down('Space');
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).sw2).toBe(true);
 await page.keyboard.up('Space');
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).sw2).toBe(false);
 const key=page.getByRole('button',{name:'E SW17 row 4 column 3',exact:true});
 await key.focus();await page.keyboard.down('Enter');
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).keys).toEqual([14]);
 await page.keyboard.up('Enter');
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).keys).toEqual([]);
 await page.setViewportSize({width:430,height:932});
 await expect(page.getByRole('heading',{name:'Virtual evaluation board'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(430);
 await page.screenshot({path:'test-results/board-mobile.png',fullPage:true});
});

test('compilation survives screen changes and disables source replacement',async({page})=>{
 let arrived!:()=>void,finishCompile!:()=>void;
 const arrival=new Promise<void>(r=>arrived=r);
 const compileGate=new Promise<void>(r=>finishCompile=r);
 await page.route('**/api/compile',async route=>{
  const response=await route.fetch();arrived();await compileGate;await route.fulfill({response});
 });
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 const original=await page.getByLabel('Embedded C editor').inputValue();
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await arrival;
 await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await page.getByRole('button',{name:'Keypad keycode on LCD',exact:true}).click();
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await expect(page.getByLabel('Embedded C editor')).toBeDisabled();
 await expect(page.getByLabel('Upload C or HEX')).toBeDisabled();
 await expect(page.getByRole('button',{name:'↑ Open C / HEX',exact:true})).toBeDisabled();
 finishCompile();
 await expect(page.getByRole('button',{name:'▶ Run',exact:true})).toBeEnabled({timeout:30000});
 await expect(page.getByLabel('Embedded C editor')).toHaveValue(original);
});

test('window blur releases inputs after queued presses',async({page,request})=>{
 // ArrowRight must change the value, even after another test used the maximum.
 await request.post('/api/physical',{data:{action:'pot',channel:5,voltage:1.65}});
 await page.reload();
 await expect(page.getByLabel('POT1 voltage')).toHaveValue('1.65');
 let release!:()=>void,arrived!:()=>void;
 const gate=new Promise<void>(r=>release=r),arrival=new Promise<void>(r=>arrived=r);
 await page.route('**/api/physical',async route=>{
  if(route.request().postDataJSON().action==='pot'){
   const response=await route.fetch();arrived();await gate;await route.fulfill({response});
  }else await route.continue();
 });
 await page.getByLabel('POT1 voltage').focus();
 await page.keyboard.press('ArrowRight');await arrival;
 await page.getByRole('button',{name:'SW2',exact:true}).focus();
 await page.keyboard.down('Space');
 await page.evaluate(()=>window.dispatchEvent(new Event('blur')));
 release();
 await expect.poll(async()=>{
  const s=await (await request.get('/api/state')).json();
  return s.sw2;
 }).toBe(false);
 // Allow the blocked queue to drain before asserting the final held state.
 await page.waitForTimeout(400);
 expect((await (await request.get('/api/state')).json()).sw2).toBe(false);
 await page.keyboard.up('Space');
});
