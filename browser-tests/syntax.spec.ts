import {test,expect} from '@playwright/test';

const sample=`#include <LPC17xx.h>
#define MASK (0xFU << 23)
// while and 123 are a comment
/* unsigned int
   not a keyword here */
__irq void handler(void) {
    unsigned int value = 0x2AU;
    const char *text = "if // <img src=x onerror=alert(1)>";
    char quote = '\\'';
    LPC_GPIO0->FIOSET = MASK;
    while (value) value--;
}
`;

test('C colors update while editing without changing text, indentation or downloads',async({page})=>{
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill(sample);
 const painted=page.locator('.code-highlight');
 await expect(painted.locator('.c-source')).toHaveText(sample,{useInnerText:false});
 await expect(painted.locator('.c-keyword').filter({hasText:'while'})).toHaveCount(1);
 await expect(painted.locator('.c-keyword').filter({hasText:'__irq'})).toHaveCount(1);
 await expect(painted.locator('.c-comment')).toHaveCount(2);
 await expect(painted.locator('.c-comment .c-keyword')).toHaveCount(0);
 await expect(painted.locator('.c-string').first()).toHaveText('"if // <img src=x onerror=alert(1)>"');
 await expect(painted.locator('.c-register')).toHaveText('LPC_GPIO0');
 await expect(painted.locator('img')).toHaveCount(0);
 const colors=await painted.evaluate(el=>['keyword','comment','string','number','preprocessor'].map(kind=>getComputedStyle(el.querySelector('.c-'+kind)!).color));
 expect(new Set(colors).size).toBe(5);
 await editor.press('Control+End');await editor.press('Tab');await editor.pressSequentially('return 123;');
 await expect(editor).toHaveValue(sample+'    return 123;');
 await expect(painted.locator('.c-source')).toHaveText(sample+'    return 123;',{useInnerText:false});
 const downloadEvent=page.waitForEvent('download');
 await page.getByRole('button',{name:'↓ C',exact:true}).click();
 const download=await downloadEvent;
 const {readFile}=await import('node:fs/promises');
 expect(await readFile((await download.path())!,'utf8')).toBe(sample+'    return 123;');
});

test('highlighted text follows both scroll axes and keeps its position across navigation',async({page})=>{
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill(Array.from({length:180},(_,i)=>`unsigned int counter_${i} = 0xFFU; // ${'long '.repeat(55)}`).join('\n'));
 await editor.evaluate((el:HTMLTextAreaElement)=>{el.setSelectionRange(1900,1910);el.scrollTop=1500;el.scrollLeft=180;el.dispatchEvent(new Event('scroll'));});
 const state=()=>page.evaluate(()=>{
  const editor=document.querySelector('textarea')!,paint=document.querySelector('.code-highlight')!;
  return {top:editor.scrollTop,left:editor.scrollLeft,paintTop:paint.scrollTop,paintLeft:paint.scrollLeft,width:editor.clientWidth,paintWidth:paint.clientWidth,height:editor.clientHeight,paintHeight:paint.clientHeight};
 });
 const before=await state();
 expect(before.top).toBeGreaterThan(0);expect(before.left).toBeGreaterThan(0);
 expect(before.paintTop).toBe(before.top);expect(before.paintLeft).toBe(before.left);
 expect(before.paintWidth).toBe(before.width);expect(before.paintHeight).toBe(before.height);
 await page.getByRole('link',{name:'Board',exact:true}).click();
 await page.getByRole('link',{name:'IDE',exact:true}).click();
 await expect(editor).toBeVisible();
 expect(await state()).toEqual(before);
 await page.setViewportSize({width:430,height:932});
 await expect.poll(async()=>{const s=await state();return s.paintWidth===s.width&&s.paintHeight===s.height&&s.paintTop===s.top&&s.paintLeft===s.left;}).toBe(true);
});

test('reference solutions use the same C highlighting and retain their exact source',async({page,request})=>{
 const {source}=await (await request.get('/api/examples/lab7_sequence')).json();
 await page.goto('/#labs');
 await page.getByRole('button',{name:'Serial LED ON / OFF',exact:true}).click();
 const code=page.getByLabel('Solution source');
 await expect(code).toHaveText(source,{useInnerText:false});
 await expect(code.locator('.c-comment').first()).toBeVisible();
 expect(await code.locator('.c-keyword').count()).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Open in IDE',exact:true}).click();
 await expect(page.getByLabel('Embedded C editor')).toHaveValue(source);
 await expect(page.locator('.code-highlight .c-source')).toHaveText(source,{useInnerText:false});
});
