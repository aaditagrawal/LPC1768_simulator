export type CTokenKind='plain'|'keyword'|'comment'|'string'|'number'|'preprocessor'|'register'|'constant';
export type CToken={kind:CTokenKind;value:string;start:number};

const keywords=new Set(`auto break case char const continue default do double else enum extern float
 for goto if inline int long register restrict return short signed sizeof static struct switch
 typedef union unsigned void volatile while _Alignas _Alignof _Atomic _Bool _Complex _Generic
 _Imaginary _Noreturn _Static_assert _Thread_local bool
 __align __asm __attribute__ __declspec __forceinline __inline __irq __packed __pure __restrict
 __schedule_barrier __softfp __svc __value_in_regs __weak __writeonly __IO __I __O
 int8_t int16_t int32_t int64_t uint8_t uint16_t uint32_t uint64_t intptr_t uintptr_t size_t
 ptrdiff_t IRQn_Type`.split(/\s+/));

// Consume comments and literals before identifiers so their contents stay inert.
// All branches accept incomplete input: highlighting also runs while a user types.
const lexeme=new RegExp([
 String.raw`(?<comment>\/\/(?:\\\r?\n|[^\r\n])*|\/\*[\s\S]*?(?:\*\/|(?![\s\S])))`,
 String.raw`(?<string>(?:u8|u|U|L)?(?:"(?:\\(?:\r\n|[\s\S])|[^"\\\r\n])*\\?"?|'(?:\\(?:\r\n|[\s\S])|[^'\\\r\n])*\\?'?))`,
 String.raw`(?<preprocessor>^[\t ]*#[\t ]*[A-Za-z_]\w*(?:[\t ]*<[^>\r\n]*>?)?)`,
 String.raw`(?<number>\b0[xX](?:[\da-fA-F]+(?:\.[\da-fA-F]*)?|\.[\da-fA-F]+)(?:[pP][+-]?\d+)?[uUlLfF]*|\b0[bB][01]+[uUlL]*|\b\d+(?:\.\d*)?(?:[eE][+-]?\d+)?[uUlLfF]*|\.\d+(?:[eE][+-]?\d+)?[fFlL]*)`,
 String.raw`(?<identifier>[A-Za-z_]\w*)`,
].join('|'),'gm');

export function tokenizeC(source:string):CToken[]{
 const tokens:CToken[]=[];
 let end=0;
 const add=(kind:CTokenKind,value:string,start:number)=>{
  const previous=tokens[tokens.length-1];
  if(kind==='plain'&&previous?.kind==='plain')previous.value+=value;
  else if(value)tokens.push({kind,value,start});
 };
 for(const match of source.matchAll(lexeme)){
  const start=match.index!,value=match[0],groups=match.groups!;
  add('plain',source.slice(end,start),end);
  let kind:CTokenKind='plain';
  if(groups.comment!==undefined)kind='comment';
  else if(groups.string!==undefined)kind='string';
  else if(groups.preprocessor!==undefined)kind='preprocessor';
  else if(groups.number!==undefined)kind='number';
  else if(keywords.has(value))kind='keyword';
  else if(/^LPC_\w+$/.test(value)||/^(?:NVIC|SCB|SysTick|DWT|ITM|CoreDebug)$/.test(value))kind='register';
  else if(/^[A-Z][A-Z0-9_]*$/.test(value)||value==='true'||value==='false')kind='constant';
  add(kind,value,start);
  end=start+value.length;
 }
 add('plain',source.slice(end),end);
 return tokens;
}
