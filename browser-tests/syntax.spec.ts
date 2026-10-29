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

test('Tab indentation cannot move the caret backward after subsequent typing',async({page})=>{
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill('int value;\n');await editor.press('Control+End');
 // Reproduce a delayed frame while keyboard input continues normally.
 await page.evaluate(()=>{
  const original=window.requestAnimationFrame,pending:FrameRequestCallback[]=[];
  window.requestAnimationFrame=callback=>pending.push(callback);
  (window as any).releaseEditorFrames=()=>{
   window.requestAnimationFrame=original;
   pending.forEach(callback=>callback(performance.now()));
  };
 });
 await editor.press('Tab');await editor.pressSequentially('re');
 await page.evaluate(()=>(window as any).releaseEditorFrames());
 await editor.pressSequentially('turn 123;');
 await expect(editor).toHaveValue('int value;\n    return 123;');
 await expect(page.locator('.code-highlight .c-source')).toHaveText('int value;\n    return 123;',{useInnerText:false});
});

const unindentCases=[
 {name:'four spaces',source:'    return;',start:11,end:11,want:'return;',selection:[7,7]},
 {name:'partial indentation',source:'  return;',start:9,end:9,want:'return;',selection:[7,7]},
 {name:'a literal tab',source:'\treturn;',start:8,end:8,want:'return;',selection:[7,7]},
 {name:'caret within indentation',source:'    return;',start:2,end:2,want:'return;',selection:[0,0]},
 {name:'unindented code',source:'return;',start:7,end:7,want:'return;',selection:[7,7]},
 {name:'an empty editor',source:'',start:0,end:0,want:'',selection:[0,0]},
 {name:'selected lines ending at the next line start',source:'    first;\n        second;\n    third;',start:4,end:27,want:'first;\n    second;\n    third;',selection:[0,19]},
 {name:'a backward selection',source:'    first;\n        second;\n    third;',start:6,end:24,direction:'backward' as const,want:'first;\n    second;\n    third;',selection:[2,16]},
 {name:'an unindented selection',source:'first;\nsecond;',start:0,end:14,want:'first;\nsecond;',selection:[0,14]},
];
for(const example of unindentCases){
 test(`Shift+Tab unindents ${example.name} and preserves the selection`,async({page})=>{
  await page.goto('/#ide');
  const editor=page.getByLabel('Embedded C editor');
  await editor.fill(example.source);
  await editor.evaluate((el:HTMLTextAreaElement,{start,end,direction})=>el.setSelectionRange(start,end,direction),
   {start:example.start,end:example.end,direction:example.direction??'forward'});
  await editor.press('Shift+Tab');
  await expect(editor).toHaveValue(example.want);
  await expect(editor).toBeFocused();
  expect(await editor.evaluate((el:HTMLTextAreaElement)=>[el.selectionStart,el.selectionEnd])).toEqual(example.selection);
  if(example.direction)expect(await editor.evaluate((el:HTMLTextAreaElement)=>el.selectionDirection)).toBe(example.direction);
  await expect(page.locator('.code-highlight .c-source')).toHaveText(example.want,{useInnerText:false});
 });
}

test('typing immediately after Shift+Tab uses the restored caret',async({page})=>{
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill('    return');await editor.press('Control+End');
 await editor.press('Shift+Tab');await editor.pressSequentially(' 123;');
 await expect(editor).toHaveValue('return 123;');
});

const newlineCases=[
 {name:'spaces',source:'    int value;',want:'    int value;\n    '},
 {name:'tabs',source:'\t\tvalue;',want:'\t\tvalue;\n\t\t'},
 {name:'mixed whitespace',source:' \t value;',want:' \t value;\n \t '},
 {name:'the current line',source:'int main(void)\n    value;',want:'int main(void)\n    value;\n    '},
 {name:'an indented blank line',source:'    ',want:'    \n    '},
 {name:'an unindented line',source:'value;',want:'value;\n'},
 {name:'an empty editor',source:'',want:'\n'},
 {name:'a split line',source:'    first;second;',start:10,end:10,want:'    first;\n    second;',caret:15},
 {name:'a replaced selection',source:'    first;\n        second;',start:4,end:26,want:'    \n    '},
 {name:'a caret inside indentation',source:'    value;',start:2,end:2,want:'  \n    value;',caret:5},
];
for(const example of newlineCases){
 test(`Enter retains indentation for ${example.name}`,async({page})=>{
  await page.goto('/#ide');
  const editor=page.getByLabel('Embedded C editor');
  await editor.fill(example.source);
  if(example.start===undefined)await editor.press('Control+End');
  else await editor.evaluate((el:HTMLTextAreaElement,{start,end})=>el.setSelectionRange(start!,end!),{start:example.start,end:example.end});
  await editor.press('Enter');
  await expect(editor).toHaveValue(example.want);
  const caret=example.caret??example.want.length;
  expect(await editor.evaluate((el:HTMLTextAreaElement)=>[el.selectionStart,el.selectionEnd])).toEqual([caret,caret]);
  await expect(page.locator('.code-highlight .c-source')).toHaveText(example.want,{useInnerText:false});
 });
}

test('typing and repeated Enter keep the indentation at the restored caret',async({page})=>{
 await page.goto('/#ide');
 const editor=page.getByLabel('Embedded C editor');
 await editor.fill('    first;');await editor.press('Control+End');
 await editor.press('Enter');await editor.pressSequentially('second;');
 await editor.press('Enter');await editor.pressSequentially('third;');
 await expect(editor).toHaveValue('    first;\n    second;\n    third;');
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
