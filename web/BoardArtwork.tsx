import {memo} from 'react';
import type {ReactNode} from 'react';
import {PhysicalSelector} from './JumperBody';

const silk='#d7e7cf';

function Section({x,y,w,h,label,children}:{x:number;y:number;w:number;h:number;label:string;children?:ReactNode}) {
 return <g>
  <rect x={x} y={y} width={w} height={h} rx="13" fill="none" stroke={silk} strokeWidth="1.5" opacity=".8"/>
  <text x={x+w/2} y={y+h-9} textAnchor="middle" fill={silk} fontSize="11" fontWeight="600" letterSpacing=".6">{label}</text>
  {children}
 </g>;
}

function Screw({x,y,r=9}:{x:number;y:number;r?:number}) {
 return <g transform={`translate(${x} ${y})`}>
  <circle r={r+3} fill="#07372e" stroke="#a0b6a1"/>
  <circle r={r} fill="url(#metal)" stroke="#626c65"/>
  <circle r={r*.65} fill="none" stroke="#e4e5ce" strokeWidth=".8"/>
  <path d={`M ${-r*.53} 0 H ${r*.53} M 0 ${-r*.53} V ${r*.53}`} stroke="#525e58" strokeWidth="2.5"/>
 </g>;
}

function Chip({x,y,w=65,h=30,label='',pins=8,vertical=false}:{x:number;y:number;w?:number;h?:number;label?:string;pins?:number;vertical?:boolean}) {
 return <g transform={`translate(${x} ${y})${vertical?' rotate(90)':''}`}>
  {Array.from({length:pins},(_,i)=><g key={i}>
   <rect x={4+i*(w-8)/pins} y="-6" width="3.5" height={h+12} rx="1" fill="#a5aaa0"/>
  </g>)}
  <rect x="-2" y="1" width={w+4} height={h+3} rx="2" fill="#032b22" opacity=".7"/>
  <rect width={w} height={h} rx="2" fill="url(#ic)" stroke="#4a5149"/>
  <path d={`M ${w/2-5} 0 a 5 5 0 0 0 10 0`} stroke="#5e665c" fill="none"/>
  <circle cx="6" cy={h-6} r="1.7" fill="#b8b9a2"/>
  {label&&<text x={w/2} y={h/2+3} textAnchor="middle" fill="#a5ad96" fontSize="7" fontFamily="monospace">{label}</text>}
 </g>;
}

function Passive({x,y,vertical=false,capacitor=false,label}:{x:number;y:number;vertical?:boolean;capacitor?:boolean;label?:string}) {
 return <g transform={`translate(${x} ${y})`}>
  <g transform={vertical?'rotate(90)':undefined}>
   <rect x="-8" y="-3" width="16" height="6" rx="1" fill="#b9bba8"/>
   <rect x="-4" y="-3" width="8" height="6" fill={capacitor?'#b79b6a':'#333e36'}/>
   {!capacitor&&<text y="1.8" textAnchor="middle" fill="#d3d7b9" fontSize="4">103</text>}
  </g>
  {label&&<text x={vertical?8:0} y={vertical?3:-6} textAnchor={vertical?'start':'middle'} fill={silk} fontSize="5.5">{label}</text>}
 </g>;
}

function Passives({x,y,n=6,step=16,vertical=false,prefix='R'}:{x:number;y:number;n?:number;step?:number;vertical?:boolean;prefix?:string}) {
 return <g>{Array.from({length:n},(_,i)=><Passive key={i} x={x+i*step} y={y} vertical={vertical} capacitor={prefix==='C'} label={`${prefix}${i+1}`}/>)}</g>;
}

function Socket({x,y,columns=5,rows=2,pitch=11,label='',vertical=false}:{x:number;y:number;columns?:number;rows?:number;pitch?:number;label?:string;vertical?:boolean}) {
 const w=columns*pitch+14,h=rows*pitch+14;
 return <g transform={`translate(${x} ${y})${vertical?' rotate(90)':''}`}>
  <rect x={-w/2-3} y={-h/2-3} width={w+6} height={h+6} fill="none" stroke={silk} strokeWidth=".8"/>
  <rect x={-w/2} y={-h/2} width={w} height={h} rx="2" fill="#101b19" stroke="#485349" strokeWidth="2"/>
  <rect x={-w/2+4} y={-h/2+4} width={w-8} height={h-8} fill="#070f0d" stroke="#303e35"/>
  {Array.from({length:columns*rows},(_,i)=><g key={i}>
   <rect x={-(columns-1)*pitch/2+(i%columns)*pitch-2} y={-(rows-1)*pitch/2+Math.floor(i/columns)*pitch-2} width="4" height="4" fill="#676b51"/>
   <rect x={-(columns-1)*pitch/2+(i%columns)*pitch-1} y={-(rows-1)*pitch/2+Math.floor(i/columns)*pitch-1} width="2" height="2" fill="#050a08"/>
  </g>)}
  <path d={`M ${-w/2-6} ${-h/2+3} l -5 4 l 5 4 z`} fill={silk}/>
  {label&&<text y={h/2+11} textAnchor="middle" fill={silk} fontSize="8">{label}</text>}
 </g>;
}

function Capacitor({x,y,r=8}:{x:number;y:number;r?:number}) {
 return <g>
  <circle cx={x+2} cy={y+3} r={r} fill="#012e25"/>
  <circle cx={x} cy={y} r={r} fill="#152e32" stroke="#aebdad" strokeWidth="2"/>
  <path d={`M ${x-r*.6} ${y-r*.6} L ${x+r*.6} ${y+r*.6} M ${x-r*.6} ${y+r*.6} L ${x+r*.6} ${y-r*.6}`} stroke="#b8c5bc" strokeWidth="1.2"/>
 </g>;
}

function DSub({x,y,label}:{x:number;y:number;label:string}) {
 return <g transform={`translate(${x} ${y})`}>
  <rect x="-70" y="-34" width="140" height="76" rx="5" fill="none" stroke={silk}/>
  <rect x="-64" y="-28" width="128" height="65" rx="4" fill="url(#metal)" stroke="#78847c" strokeWidth="2"/>
  <path d="M -44 -23 H 44 L 37 27 H -37 Z" fill="#22465c" stroke="#d1d9d3" strokeWidth="3"/>
  {[0,1,2,3,4,5,6,7,8].map(i=><circle key={i} cx={i<5?-30+i*15:-23+(i-5)*15} cy={i<5?-6:10} r="3" fill="#bbab76" stroke="#132830"/>)}
  <Screw x={-55} y={4} r={5}/><Screw x={55} y={4} r={5}/>
  <text x="0" y="54" textAnchor="middle" fontSize="8" fill={silk}>{label}</text>
 </g>;
}

function Dip({x,y,label,count=2}:{x:number;y:number;label:string;count?:number}) {
 return <g transform={`translate(${x} ${y})`}>
  <rect x="-15" y="-20" width="30" height="40" rx="2" fill="#c42d3e" stroke="#f17a71"/>
  <text y="-11" textAnchor="middle" fontSize="5" fill="#fff">ON</text>
  {Array.from({length:count},(_,i)=><g key={i}>
   <rect x={-9+i*11} y="-5" width="7" height="15" fill="#811b2a"/>
   <rect x={-8+i*11} y="-4" width="5" height="7" rx="1" fill="#fff2d2"/>
   <text x={-5+i*11} y="17" fontSize="5" textAnchor="middle" fill="white">{i+1}</text>
  </g>)}
  <text y="32" textAnchor="middle" fontSize="7" fill={silk}>{label}</text>
 </g>;
}

function Terminal({x,y,n=2}:{x:number;y:number;n?:number}) {
 return <g transform={`translate(${x} ${y})`}>
  <rect x="-13" y="-10" width={n*16+7} height="26" rx="3" fill="#8cad51" stroke="#c8d4a6"/>
  {Array.from({length:n},(_,i)=><g key={i}><circle cx={i*16} cy="2" r="5.5" fill="#cbd1b5" stroke="#6b795d"/><path d={`M ${i*16-3} -1 l 6 6`} stroke="#5c6655" strokeWidth="1.5"/></g>)}
 </g>;
}

function Relay({x,y,label}:{x:number;y:number;label:string}) {
 return <g transform={`translate(${x} ${y})`}>
  <rect width="100" height="43" rx="3" fill="#162b3b" stroke="#7c9393"/>
  <text x="50" y="14" textAnchor="middle" fontSize="8" fill="#9caeb1">HRS4H-S-DC5V</text>
  <text x="50" y="27" textAnchor="middle" fontSize="7" fill="#9caeb1">3A 120VAC</text>
  <text x="50" y="37" textAnchor="middle" fontSize="6" fill="#9caeb1">3A 24VDC</text>
  <text x="-12" y="25" fontSize="8" fill={silk}>{label}</text>
 </g>;
}

export const BoardArtwork=memo(function BoardArtwork() {
 return <g className="board-artwork" pointerEvents="none" fontFamily="Arial, sans-serif">
  <defs>
   <linearGradient id="pcb" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#09644d"/><stop offset=".5" stopColor="#064d40"/><stop offset="1" stopColor="#075846"/></linearGradient>
   <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#e1e4d7"/><stop offset=".22" stopColor="#a1b0a5"/><stop offset=".52" stopColor="#d1dbce"/><stop offset=".8" stopColor="#8b9a90"/><stop offset="1" stopColor="#d9dfd2"/></linearGradient>
   <linearGradient id="ic" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#303c35"/><stop offset=".2" stopColor="#17221d"/><stop offset="1" stopColor="#0d1713"/></linearGradient>
   <radialGradient id="led-lens"><stop stopColor="#8c3f29"/><stop offset=".6" stopColor="#5a251e"/><stop offset="1" stopColor="#2c2418"/></radialGradient>
   <pattern id="pcb-grain" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".55" fill="#a3c4a0" opacity=".09"/><circle cx="7" cy="8" r=".5" fill="#001f1c" opacity=".15"/></pattern>
   <pattern id="plate-grain" width="7" height="7" patternUnits="userSpaceOnUse"><path d="M0 2h5M2 5h5" stroke="#385d50" strokeWidth=".5" opacity=".13"/></pattern>
  </defs>
  {/* Uncabled, top-down reconstruction of the supplied ALS board photograph. */}
  <rect x="17" y="20" width="1408" height="1005" rx="24" fill="#050d0b"/>
  <rect x="25" y="23" width="1390" height="991" rx="18" fill="#102f29" stroke="#2a3c33" strokeWidth="4"/>
  <rect x="35" y="32" width="1370" height="972" rx="12" fill="url(#pcb)" stroke="#75aa86" strokeWidth="2"/>
  <rect x="35" y="32" width="1370" height="972" rx="12" fill="url(#pcb-grain)"/>
  <g fill="none" stroke="#72ac7d" strokeWidth="1" opacity=".28">
   {Array.from({length:13},(_,i)=><path key={i} d={`M ${315+i*5} ${105+i*10} H ${330+i*5} V ${360+i*3} H ${490+i*9} L ${520+i*9} ${390+i*3} H 735`}/>)}
   {Array.from({length:10},(_,i)=><path key={i} d={`M ${788+i*4} ${430+i*18} H ${828+i*3} V ${350+i*8} H ${1090-i*8}`}/>)}
   {Array.from({length:8},(_,i)=><path key={i} d={`M ${310-i*5} ${450+i*13} H ${432-i*3} L ${475-i*3} ${493+i*13}`}/>)}
   {Array.from({length:12},(_,i)=><path key={i} d={`M ${520+i*17} 730 V ${745+i*3} L ${544+i*17} ${769+i*3} H ${810+i*6}`}/>)}
   {Array.from({length:8},(_,i)=><path key={i} d={`M ${103+i*24} 880 V ${910+i*3} H ${94+i*26} V 951`}/>)}
   <path d="M 72 263 H 282 V 390 H 308 M 60 425 H 90 L 107 442 H 269 M 1155 322 V 477 H 1378 M 1120 768 H 1154 L 1175 790 H 1374"/>
  </g>
  <g fill="#b7c793" opacity=".6">{Array.from({length:16},(_,i)=><circle key={i} cx={476+i*20} cy={369+(i%3)*6} r="1.8"/>)}</g>
  {[ [51,49],[1388,49],[51,987],[1388,987] ].map(([x,y],i)=><Screw key={i} x={x} y={y} r={10}/>)}

  <Section x={54} y={65} w={262} h={235} label="UART0 AND UART3 INTERFACE">
   <DSub x={185} y={76} label="CN9"/>
   <Chip x={162} y={181} w={57} h={24} label="MAX3232"/>
   <Passives x={174} y={151} n={4} step={18} vertical prefix="C"/>
   <Passives x={163} y={232} n={4} step={20} vertical prefix="C"/>
   <Dip x={271} y={249} label="SW21"/>
   <rect x="60" y="160" width="19" height="26" fill="#dddac1" stroke="#97a483"/>
   <Passives x={103} y={183} n={2}/>
   <text x="99" y="219" fill={silk} fontSize="8">U13</text>
  </Section>
  <Section x={330} y={65} w={494} h={298} label="GRAPHIC AND ALPHANUMERIC LCD">
   <rect x="350" y="64" width="366" height="182" rx="3" fill="#248140" stroke="#9ebc7b" strokeWidth="2"/>
   <rect x="363" y="84" width="340" height="110" rx="4" fill="#111e17" stroke="#354a2e" strokeWidth="8"/>
   <rect x="374" y="94" width="317" height="88" rx="3" fill="#21320d"/>
   <rect x="384" y="102" width="284" height="66" fill="#54712a"/>
   {Array.from({length:16},(_,i)=><rect key={i} x={377+i*19} y="65" width="5" height="9" fill="#b8c7a6"/>)}
   {[[358,76],[707,76],[358,234],[707,234]].map(([x,y],i)=><Screw key={i} x={x} y={y} r={5}/>)}
   <text x="529" y="265" textAnchor="middle" fill={silk} fontSize="11" letterSpacing="1">ALPHANUMERIC LCD</text>
   <rect x="352" y="278" width="85" height="24" fill="#e4e8d3"/>
   <text x="394" y="295" textAnchor="middle" fill="#455549" fontSize="15">2015</text>
   <Socket x={571} y={322} columns={20} pitch={9}/>
   <text x="571" y="295" textAnchor="middle" fill={silk} fontSize="8">CN10 · GRAPHIC LCD</text>
   <circle cx="749" cy="83" r="13" fill="#a9c2a1" stroke="#2682a2" strokeWidth="5"/>
   <path d="M742 90l14-15" stroke="#355448" strokeWidth="3"/>
   <text x="749" y="60" textAnchor="middle" fill={silk} fontSize="7">LCD CONTRAST</text>
   <Socket x={780} y={236} vertical label="CND1"/>
   <Capacitor x={756} y={332} r={6}/>
   <PhysicalSelector x={780} y={337} name="JP17"/>
  </Section>
  <Section x={840} y={65} w={270} h={255} label="7 SEGMENT DISPLAY">
   <rect x="851" y="67" width="248" height="100" rx="3" fill="#111b17" stroke="#a8bba0"/>
   <Passives x={873} y={190} n={10} step={22} vertical/>
   <Chip x={862} y={213} w={104} h={31} pins={10} label="U12 BUFFER"/>
   <Chip x={995} y={213} w={100} h={31} pins={8} label="U7 BCD DECODER"/>
  </Section>
  <Section x={1125} y={65} w={262} h={255} label="POWER SUPPLY">
   <DSub x={1257} y={76} label="CN8"/>
   <Capacitor x={1156} y={171} r={9}/><Capacitor x={1156} y={259} r={13}/>
   <circle cx="1183" cy="161" r="4" fill="#e4edb0" stroke="#a3b796"/>
   <text x="1193" y="165" fill={silk} fontSize="8">+5V</text>
   <rect x="1210" y="188" width="65" height="85" rx="3" fill="#111e1c" stroke="#48655b"/>
   {[0,1,2,3].map(i=><path key={i} d={`M ${1216+i*16} 195 v 63`} stroke="#657064" strokeWidth="6"/>)}
   <Chip x={1285} y={207} w={42} h={24} pins={3} label="3.3V"/>
   <Passives x={1150} y={217} n={3} step={20}/>
   <Socket x={1345} y={220} columns={1} rows={3} label="TP1"/>
   <text x="1320" y="281" fill={silk} fontSize="8">GND</text>
  </Section>

  <Section x={54} y={314} w={262} h={350} label="ETHERNET">
   <rect x="70" y="329" width="160" height="22" rx="10" fill="none" stroke={silk}/>
   <text x="150" y="344" textAnchor="middle" fill={silk} fontSize="10">www.alsindia.net</text>
   <rect x="40" y="363" width="87" height="74" rx="3" fill="url(#metal)" stroke="#c9d0c4" strokeWidth="2"/>
   <rect x="38" y="376" width="61" height="49" fill="#151f1b"/>
   <rect x="45" y="383" width="43" height="35" fill="#071813" stroke="#788675"/>
   <path d="M50 383v10m5-10v10m5-10v10m5-10v10m5-10v10m5-10v10" stroke="#a3aa6b" strokeWidth="2"/>
   <rect x="151" y="374" width="112" height="21" rx="2" fill="#dee4cf"/>
   <text x="207" y="389" textAnchor="middle" fill="#63866b" fontSize="10" fontStyle="italic">P4331/2</text>
   <Chip x={168} y={485} w={47} h={47} pins={7} label="ENC28J60"/>
   <g transform="translate(208 557)"><rect x="-22" y="-36" width="49" height="91" rx="7" fill="url(#metal)" stroke="#ced4c2" strokeWidth="2"/><text transform="rotate(90)" y="3" textAnchor="middle" fill="#718277" fontSize="9">25.000 MHz</text></g>
   <Capacitor x={113} y={569}/><Capacitor x={130} y={599}/>
   <Passives x={83} y={459} n={8} step={28}/><Passives x={83} y={553} n={4} step={27}/>
   <Passives x={80} y={626} n={8} step={28} prefix="C"/>
   <Passives x={250} y={462} n={2} step={22} vertical prefix="C"/>
   <circle cx="113" cy="584" r="6" fill="#c89828" stroke="#e5d48b"/>
  </Section>

  <Section x={330} y={377} w={78} h={78} label="AD0.4"/>
  <Section x={330} y={467} w={78} h={78} label="AD0.5"/>
  <Section x={419} y={377} w={61} h={78} label="CLKOUT"><circle cx="449" cy="401" r="4" fill="#d9d9ad"/><text x="449" y="392" fill={silk} textAnchor="middle" fontSize="7">TP9</text></Section>
  <Section x={419} y={467} w={61} h={78} label="INT DAC"><circle cx="449" cy="491" r="4" fill="#d9d9ad"/><text x="449" y="482" fill={silk} textAnchor="middle" fontSize="7">TP8</text></Section>
  <Section x={330} y={557} w={78} h={96} label="ISP"><Passives x={347} y={580} n={2} step={24} vertical/><Chip x={352} y={609} w={26} h={16} pins={3}/></Section>
  <rect x="489" y="423" width="300" height="307" rx="12" fill="#022c24" stroke="#d0dfc3"/>
  <rect x="497" y="431" width="285" height="289" rx="8" fill="url(#metal)" stroke="#e1e7d7" strokeWidth="2"/>
  <rect x="497" y="431" width="285" height="289" rx="8" fill="url(#plate-grain)"/>
  <rect x="559" y="486" width="167" height="166" fill="#67927f" opacity=".22"/>
  <rect x="601" y="523" width="90" height="90" rx="3" fill="#465e52" opacity=".18"/>
  <text x="640" y="495" textAnchor="middle" fill="#5b7d69" opacity=".65" fontSize="12">LPC1768</text>
  <text x="640" y="514" textAnchor="middle" fill="#5b7d69" opacity=".6" fontSize="8">ARM CORTEX-M3</text>
  <rect x="609" y="670" width="42" height="43" fill="#f0eee1" stroke="#17251b" strokeWidth="2"/>
  <text x="630" y="701" textAnchor="middle" fill="#1d2b24" fontSize="25">20</text>
  {[[511,445],[768,445],[511,705],[768,705]].map(([x,y],i)=><Screw key={i} x={x} y={y}/>)}
  <text transform="translate(839 644) rotate(-90)" fill={silk} fontSize="8" letterSpacing="1">LPC1768 EVALUATION BASE</text>
  <text x="642" y="782" textAnchor="middle" fill={silk} fontSize="10">99-89-14</text>
  <Section x={330} y={665} w={150} h={124} label="RESET">
   <Passives x={390} y={694} n={3} step={24} vertical/>
   <Passives x={392} y={733} n={3} step={24}/>
   <text x="350" y="676" textAnchor="middle" fill={silk} fontSize="8">SW1</text>
  </Section>

  <Section x={840} y={333} w={270} h={61} label="I2S"><Socket x={898} y={355}/><Passives x={968} y={354} n={6} step={21}/></Section>
  <Section x={840} y={405} w={270} h={80} label="NIFC"><Socket x={973} y={438} columns={16} pitch={12}/></Section>
  <Section x={840} y={499} w={116} h={235} label="JTAG"><Socket x={877} y={603} columns={10} vertical/><Passives x={919} y={536} n={2} step={19} vertical/><Chip x={935} y={558} w={111} h={13} pins={9} vertical/></Section>
  <Section x={969} y={499} w={141} h={235} label="TRACE"><Socket x={1067} y={602} columns={10} vertical/><Chip x={1017} y={553} w={101} h={15} pins={8} vertical/></Section>
  <Section x={1125} y={333} w={80} h={127} label="BUZZER"><circle cx="1165" cy="371" r="25" fill="#172b26" stroke="#77947f" strokeWidth="2"/><circle cx="1165" cy="371" r="3" fill="#050e0a"/><Passives x={1147} y={426} n={3} step={17}/></Section>
  <Section x={1217} y={333} w={170} h={96} label="RELAY CONTROL"><Relay x={1242} y={346} label="K1"/><Terminal x={1360} y={358}/></Section>
  <Section x={1125} y={473} w={262} h={128} label="DC MOTOR CONTROL"><Relay x={1242} y={444} label="K2"/><Terminal x={1360} y={456}/><Chip x={1247} y={532} w={107} h={34} label="L293D"/><Passives x={1149} y={513} n={5} step={18} vertical/><Passives x={1149} y={551} n={5} step={18} vertical/></Section>
  <Section x={1125} y={616} w={262} h={160} label="STEPPER MOTOR CONTROL"><Socket x={1169} y={679} vertical columns={4}/><rect x="1330" y="640" width="47" height="101" rx="3" fill="#d9ddca" stroke="#a5b79b"/>{[0,1,2,3].map(i=><rect key={i} x="1340" y={651+i*21} width="24" height="9" fill="#788a71"/>)}<Passives x={1213} y={716} n={5} step={22} vertical/><rect x="1224" y="642" width="85" height="13" rx="6" fill="#a8573d" stroke="#d2a688"/><text x="1265" y="634" textAnchor="middle" fill={silk} fontSize="7">R15</text></Section>

  <Section x={54} y={679} w={57} h={111} label="COMP"><Passive x={82} y={710} vertical/><rect x="69" y="747" width="24" height="19" fill="#d4d9be"/><text x="83" y="694" textAnchor="middle" fill={silk} fontSize="7">MAT</text></Section>
  <Section x={122} y={679} w={70} h={111} label="EX INT"><Capacitor x={152} y={750} r={6}/><text x="152" y="686" textAnchor="middle" fill={silk} fontSize="7">SW2</text></Section>
  <Section x={203} y={679} w={113} h={111} label="PWM"><Capacitor x={215} y={707} r={7}/><text x="219" y="775" textAnchor="middle" fill={silk} fontSize="7">LD10</text></Section>
  <Section x={54} y={805} w={262} h={180} label="GENERAL PURPOSE LEDS">
   <Passives x={92} y={890} n={8} step={26} vertical/>
   {[0,1,2,3,4,5,6,7].map(i=><g key={i}><path d={`M${94+i*26} 902v16m0 17v13`} stroke="#b9c9a3" strokeWidth="1.5"/><text x={94+i*26} y="958" textAnchor="middle" fill={silk} fontSize="7">LD{9-i}</text></g>)}
   <circle cx="285" cy="846" r="4" fill="#bcc8a0"/>
   <text x="285" y="833" textAnchor="middle" fill={silk} fontSize="7">TP7</text>
  </Section>
  <Section x={330} y={805} w={91} h={180} label="SPI">
   <PhysicalSelector x={351} y={829} name="JP12"/>
   <PhysicalSelector x={400} y={829} name="JP13"/>
   <Chip x={346} y={898} w={53} h={31} label="25LC"/><Passives x={345} y={874} n={4} step={20} vertical/><Socket x={375} y={942} columns={2}/>
  </Section>
  <Section x={433} y={805} w={117} h={180} label="RS485"><Socket x={490} y={833} columns={4}/><Passives x={448} y={876} n={6} step={18} vertical/><Chip x={456} y={905} w={69} h={30} label="MAX485"/><rect x="482" y="944" width="35" height="17" rx="2" fill="#dddcc5"/></Section>
  <Section x={562} y={805} w={103} h={180} label="I2C"><circle cx="612" cy="861" r="39" fill="#122c25" stroke="#b6c9ab" strokeWidth="2"/><circle cx="612" cy="861" r="31" fill="url(#metal)" stroke="#889a87" strokeWidth="2"/><path d="M612 832v55" stroke="#7a8a76" strokeWidth="9"/><text x="612" y="913" textAnchor="middle" fill={silk} fontSize="8">CR2032  BT1</text><Chip x={580} y={936} w={64} h={20} pins={4} label="PCF8563"/></Section>
  <Section x={677} y={805} w={147} h={180} label="CAN INTERFACE">
   <PhysicalSelector x={714} y={829} name="JP8"/>
   <PhysicalSelector x={783} y={829} name="JP7"/>
   <Passives x={695} y={866} n={6} step={21} vertical/><Chip x={694} y={883} w={43} h={34} pins={4} label="U27"/><Chip x={759} y={883} w={43} h={34} pins={4} label="U28"/><rect x="729" y="942" width="56" height="18" rx="3" fill="#d9ddc6"/><Passives x={695} y={930} n={6} step={21} vertical prefix="C"/>
  </Section>
  <Section x={840} y={750} w={270} h={235} label="4X4 KEY MATRIX"/>
  <Section x={1125} y={790} w={262} h={114} label="USB HOST INTERFACE">
   <Dip x={1159} y={838} label="SW19"/>
   <Chip x={1241} y={828} w={48} h={32} label="U15"/>
   <Passives x={1208} y={813} n={6} step={23}/>
   <rect x="1319" y="810" width="77" height="60" rx="3" fill="url(#metal)" stroke="#cad0bf" strokeWidth="2"/>
   <rect x="1336" y="820" width="63" height="39" fill="#12241c" stroke="#6c7e6d"/>
   <rect x="1342" y="835" width="45" height="11" fill="#c7d2b9"/>
   <path d="M1348 835v10m9-10v10m9-10v10m9-10v10" stroke="#c3aa60" strokeWidth="3"/>
  </Section>
  <Section x={1125} y={916} w={262} h={69} label="USB DEVICE INTERFACE">
   <Dip x={1159} y={940} label=""/>
   <text x="1181" y="946" fill={silk} fontSize="7">SW20</text>
   <Chip x={1245} y={930} w={45} h={23} pins={4}/><Passives x={1198} y={949} n={3} step={16} vertical/>
   <path d="M1326 917H1394V965H1326Z" fill="url(#metal)" stroke="#d0d7c3" strokeWidth="2"/>
   <path d="M1350 928H1387V953H1350L1343 946V935Z" fill="#10201a" stroke="#8b9b88" strokeWidth="2"/>
  </Section>
 </g>;
});
