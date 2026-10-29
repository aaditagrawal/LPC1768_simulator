import {test,expect} from '@playwright/test';
import {tokenizeC} from '../web/cSyntax';

test('comments and escaped literals keep apparent C code inside their own category',()=>{
 const source='// if 123\\\ncontinued\n/* while 42 */ const char *s = "return \\"quoted\\" //"; char c = \'\\\'\';';
 const tokens=tokenizeC(source);
 expect(tokens.filter(t=>t.kind==='comment').map(t=>t.value)).toEqual(['// if 123\\\ncontinued','/* while 42 */']);
 expect(tokens.filter(t=>t.kind==='keyword').map(t=>t.value)).toEqual(['const','char','char']);
 expect(tokens.filter(t=>t.kind==='string').map(t=>t.value)).toEqual(['"return \\"quoted\\" //"',"'\\''"]);
 expect(tokens.map(t=>t.value).join('')).toBe(source);
});

test('decimal, hex, binary and floating literals include their embedded C suffixes',()=>{
 const source='0 077U 0xFFUL 0b1010u 1. .5f 1e-3F 0x1.fp+2L';
 expect(tokenizeC(source).filter(t=>t.kind==='number').map(t=>t.value)).toEqual(['0','077U','0xFFUL','0b1010u','1.','.5f','1e-3F','0x1.fp+2L']);
});

test('preprocessor lines, ARM compiler extensions and CMSIS types are distinguished',()=>{
 const source='  #include <LPC17xx.h>\n#define MASK (1U << 4) \\\n | 2U\n__irq __packed volatile uint32_t __IO LPC_GPIO0 MASK;';
 const tokens=tokenizeC(source);
 expect(tokens.filter(t=>t.kind==='preprocessor').map(t=>t.value)).toEqual(['  #include <LPC17xx.h>','#define']);
 expect(tokens.filter(t=>t.kind==='keyword').map(t=>t.value)).toEqual(['__irq','__packed','volatile','uint32_t','__IO']);
 expect(tokens.filter(t=>t.kind==='register').map(t=>t.value)).toEqual(['LPC_GPIO0']);
 expect(tokens.map(t=>t.value).join('')).toBe(source);
});

test('unfinished editing states and non-ASCII text preserve every character',()=>{
 for(const source of ['', '/* unfinished\nwhile 42', '"unfinished', "'\\", '// λ ≤ 3\nint café;\n', '\t\r\n#define VALUE 1\r\n']){
  expect(tokenizeC(source).map(t=>t.value).join('')).toBe(source);
 }
 expect(tokenizeC('/* unfinished\nwhile 42').map(t=>t.kind)).toEqual(['comment']);
});
