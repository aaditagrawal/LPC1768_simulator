import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('selected exercises show and download their exact existing C solutions',async({page,request})=>{
 await page.goto('/#labs');
 for(const [id,title] of [['lab7_sequence','Serial LED ON / OFF'],['lab6_switch','SW2 controls LD2']]){
  const {source}=await (await request.get(`/api/examples/${id}`)).json();
  await page.getByRole('button',{name:title,exact:true}).click();
  await expect(page.getByRole('heading',{name:'Solution code',exact:true})).toBeVisible();
  await expect(page.getByLabel('Solution source')).toHaveText(source,{useInnerText:false});
  expect(await page.getByLabel('Solution source').textContent()).toBe(source);
  const downloadEvent=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download C',exact:true}).click();
  const download=await downloadEvent;
  expect(download.suggestedFilename()).toBe(`${id}.c`);
  expect(await readFile((await download.path())!,'utf8')).toBe(source);
 }
 await page.setViewportSize({width:430,height:932});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(430);
 await expect(page.getByLabel('Solution source')).toBeVisible();
});

test('viewing solutions preserves source, loaded firmware, cables and jumpers',async({page,request})=>{
 await page.goto('/#ide');
 const source='#include <LPC17xx.h>\nint main(void) {SystemInit();while(1) {}}\n';
 await page.getByLabel('Embedded C editor').fill(source);
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await expect(page.getByText('C source · compiled',{exact:true})).toBeVisible();
 await request.post('/api/physical',{data:{action:'connect',a:'CNA',b:'CNA1'}});
 await request.post('/api/physical',{data:{action:'jumper',name:'JP5',value:'closed'}});
 const before=await (await request.get('/api/state')).json();
 await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
 await expect(page.getByLabel('Solution source')).toContainText('int main');
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await expect(page.getByLabel('Embedded C editor')).toHaveValue(source);
 await expect(page.getByText('C source · compiled',{exact:true})).toBeVisible();
 const after=await (await request.get('/api/state')).json();
 for(const key of ['loaded','firmwareName','status','cables','jumpers','pc'])expect(after[key]).toEqual(before[key]);
});

test('Open in IDE explicitly replaces the source, resets editor position and requires compilation',async({page,request})=>{
 const {source}=await (await request.get('/api/examples/lab6_switch')).json();
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill(Array.from({length:200},(_,i)=>`// ${i} ${'x'.repeat(240)}`).join('\n'));
 await editor.evaluate((el:HTMLTextAreaElement)=>{el.setSelectionRange(1900,1910);el.scrollTop=2500;el.scrollLeft=180;});
 await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
 await expect(page.getByLabel('Solution source')).toHaveText(source,{useInnerText:false});
 await page.getByRole('button',{name:'Open in IDE',exact:true}).click();
 await expect(page).toHaveURL(/#ide$/);
 await expect(editor).toHaveValue(source);
 await expect(page.getByText('C source · compile pending',{exact:true})).toBeVisible();
 expect(await editor.evaluate((el:HTMLTextAreaElement)=>({start:el.selectionStart,end:el.selectionEnd,top:el.scrollTop,left:el.scrollLeft}))).toEqual({start:0,end:0,top:0,left:0});
 expect(await page.evaluate(()=>localStorage.getItem('lpc-lab-source'))).toBe(source);
});

test('switching exercises discards an older response and never opens stale code',async({page,request})=>{
 const first=await (await request.get('/api/examples/lab6_switch')).json();
 const second=await (await request.get('/api/examples/lab7_binary')).json();
 let release!:()=>void;
 const waiting=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/api/examples/lab6_switch',async route=>{await waiting;await route.fulfill({json:first});});
 await page.goto('/#labs');
 const pending=page.waitForRequest('**/api/examples/lab6_switch');
 await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
 await pending;
 await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'8-bit binary up counter',exact:true}).click();
 await expect(page.getByLabel('Solution source')).toHaveText(second.source,{useInnerText:false});
 const oldResponse=page.waitForResponse('**/api/examples/lab6_switch');release();await oldResponse;
 await page.getByRole('button',{name:'Open in IDE',exact:true}).click();
 await expect(page.getByLabel('Embedded C editor')).toHaveValue(second.source);
});

test('solution replacement is disabled until an in-flight compilation finishes',async({page,request})=>{
 const {source}=await (await request.get('/api/examples/lab6_switch')).json();
 let release!:()=>void;
 const waiting=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/api/compile',async route=>{const response=await route.fetch();await waiting;await route.fulfill({response});});
 await page.goto('/#ide');
 const original='int main(void) {while(1) {}}';
 await page.getByLabel('Embedded C editor').fill(original);
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
 await expect(page.getByLabel('Solution source')).toHaveText(source,{useInnerText:false});
 await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeDisabled();
 release();
 await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Open in IDE',exact:true}).click();
 await expect(page.getByLabel('Embedded C editor')).toHaveValue(source);
 await expect(page.getByText('C source · compile pending',{exact:true})).toBeVisible();
});

test('opening a solution cancels a pending file read',async({page,request})=>{
 const {source}=await (await request.get('/api/examples/lab6_switch')).json();
 await page.addInitScript(()=>{
  const read=File.prototype.text;
  File.prototype.text=async function(){const text=await read.call(this);return new Promise<string>(resolve=>{(window as any).finishFileRead=()=>resolve(text);});};
 });
 await page.goto('/#ide');
 await page.getByLabel('Upload C or HEX').setInputFiles({name:'late.c',mimeType:'text/plain',buffer:Buffer.from('// stale upload')});
 await expect.poll(()=>page.evaluate(()=>typeof (window as any).finishFileRead)).toBe('function');
 await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
 await expect(page.getByLabel('Solution source')).toHaveText(source,{useInnerText:false});
 await page.getByRole('button',{name:'Open in IDE',exact:true}).click();
 await page.evaluate(()=>{(window as any).finishFileRead();});
 await expect(page.getByLabel('Embedded C editor')).toHaveValue(source);
});

test('a failed solution request reports the error and permits retry without changing source',async({page})=>{
 await page.route('**/api/examples/lab6_switch',route=>route.fulfill({status:503,json:{error:'Example temporarily unavailable'}}));
 await page.goto('/#labs');
 await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
 await expect(page.getByRole('alert')).toHaveText('Example temporarily unavailable');
 await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeDisabled();
 await page.unroute('**/api/examples/lab6_switch');
 await page.getByRole('button',{name:'Retry',exact:true}).click();
 await expect(page.getByLabel('Solution source')).toContainText('int main');
 await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeEnabled();
});

test('a submitted HEX upload blocks source replacement and compilation until it settles',async({page,request})=>{
 const firmware=await (await request.post('/api/compile',{data:{source:'int main(void) {while(1) {}}'}})).json();
 let release!:()=>void;
 const waiting=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/api/firmware',async route=>{await waiting;await route.continue();});
 await page.goto('/#ide');
 const submitted=page.waitForRequest('**/api/firmware');
 await page.getByLabel('Upload C or HEX').setInputFiles({name:'delayed.hex',mimeType:'text/plain',buffer:Buffer.from(firmware.hex)});
 await submitted;
 try {
  await expect(page.getByRole('button',{name:/Compile C|Loading HEX/})).toBeDisabled();
  await page.getByRole('link',{name:'Lab exercises',exact:true}).click();
  await page.getByRole('button',{name:'SW2 controls LD2',exact:true}).click();
  await expect(page.getByLabel('Solution source')).toContainText('int main');
  await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeDisabled();
 } finally {
  release();
 }
 await expect(page.getByRole('button',{name:'Open in IDE',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Open in IDE',exact:true}).click();
 await expect(page.getByText('C source · compile pending',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await expect(page.getByText('C source · compiled',{exact:true})).toBeVisible();
 const state=await (await request.get('/api/state')).json();
 expect(state.firmwareName).toBe('Compiled C program');
});
