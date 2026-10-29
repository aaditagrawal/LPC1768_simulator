import {test,expect} from '@playwright/test';

test('board, IDE and exercises occupy separate screens and retain the source',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Virtual evaluation board'})).toBeVisible();
 await expect(page.getByLabel('Embedded C editor')).toHaveCount(0);
 const navigation=page.getByRole('navigation',{name:'Workspace'});
 await navigation.getByRole('link',{name:'IDE',exact:true}).click();
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill('#include <LPC17xx.h>\nint main(void) { while(1) {} }\n');
 await expect(page.getByLabel('Virtual board panel')).toHaveCount(0);
 await navigation.getByRole('link',{name:'Lab exercises',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Lab exercises',exact:true})).toBeVisible();
 await expect(editor).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Keypad keycode on LCD',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Keypad keycode on LCD',exact:true}).click();
 await navigation.getByRole('link',{name:'IDE',exact:true}).click();
 await expect(editor).toHaveValue('#include <LPC17xx.h>\nint main(void) { while(1) {} }\n');
 await expect(page.locator('.line-number-gutter pre')).toHaveText('1\n2\n3');
 await page.goBack();
 await expect(page.getByRole('heading',{name:'Lab exercises',exact:true})).toBeVisible();
 await page.goto('/#ide');
 await expect(editor).toHaveValue('#include <LPC17xx.h>\nint main(void) { while(1) {} }\n');
});

test('all screens omit hints and connection answers',async({page})=>{
 for(const screen of ['board','ide','labs']){
  await page.goto(`/#${screen}`);
  await expect(page.getByRole('navigation',{name:'Workspace'})).toBeVisible();
  const repository=page.getByRole('contentinfo').getByRole('link',{name:'View on GitHub'});
  await expect(repository).toHaveAttribute('href','https://github.com/h4rshupadhyay/LPC1768_simulator');
  await expect(repository).toHaveAttribute('target','_blank');
  await expect(repository).toHaveAttribute('rel','noopener noreferrer');
  await expect(page.getByText(/Show required physical setup|Check Connections|Load reference C|Pin mappings and SW2|Execution evidence|click headers to connect/i)).toHaveCount(0);
  await expect(page.locator('details,.connector-detail,.board-instructions')).toHaveCount(0);
  await expect(page.locator('title').filter({hasText:/P0\.|P2\.|Pins:|JP18 2/})).toHaveCount(0);
  await page.setViewportSize({width:430,height:932});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(430);
 }
});

test('leaving the board releases held hardware inputs',async({page,request})=>{
 await page.goto('/#board');
 const sw=page.getByRole('button',{name:'SW2',exact:true});
 await sw.focus();await page.keyboard.down('Space');
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).sw2).toBe(true);
 await page.evaluate(()=>{location.hash='ide';});
 await expect(page.getByLabel('Embedded C editor')).toBeVisible();
 await expect.poll(async()=> (await (await request.get('/api/state')).json()).sw2).toBe(false);
 await page.keyboard.up('Space');
});

test('compiler errors remain visible after visiting the board',async({page})=>{
 await page.goto('/#ide');
 await page.getByLabel('Embedded C editor').fill('int main( {');
 await page.getByRole('button',{name:'Compile C',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText(/error/i);
 await page.getByRole('link',{name:'Board',exact:true}).click();
 const released=page.waitForResponse(response=>response.url().endsWith('/api/physical')&&response.request().postDataJSON()?.action==='release-inputs');
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await released;
 await expect(page.getByRole('alert')).toContainText(/error/i);
});

test('returning to the IDE restores the cursor and both scroll positions',async({page})=>{
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill(Array.from({length:200},(_,i)=>`// ${i} ${'x'.repeat(240)}`).join('\n'));
 const before=await editor.evaluate((el:HTMLTextAreaElement)=>{
  el.setSelectionRange(1900,1910);el.scrollTop=2500;el.scrollLeft=180;
  el.dispatchEvent(new Event('scroll'));
  return {start:el.selectionStart,end:el.selectionEnd,top:el.scrollTop,left:el.scrollLeft};
 });
 await page.getByRole('link',{name:'Board',exact:true}).click();
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await expect(editor).toBeVisible();
 expect(await editor.evaluate((el:HTMLTextAreaElement)=>({start:el.selectionStart,end:el.selectionEnd,top:el.scrollTop,left:el.scrollLeft}))).toEqual(before);
 const offset=await page.locator('.line-number-gutter pre').evaluate(el=>new DOMMatrix(getComputedStyle(el).transform).m42);
 expect(offset).toBe(-before.top);
});
