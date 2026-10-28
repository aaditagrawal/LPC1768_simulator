import { useState } from 'react';
import type {Info,State,Layout} from './types';
import {BoardArtwork} from './BoardArtwork';
import {JumperBody} from './JumperBody';
import mapping from '../board/mapping.json';

type Props={info:Info;state:State;layout:Layout;physical:(data:unknown)=>Promise<void>;control:(action:string)=>void};
const physicalJumpers:Record<string,{pinCount:number}>=mapping.jumpers;

const segmentPolygons=[
 '8,3 34,3 39,7 34,11 8,11 4,7', '36,12 40,8 44,12 40,32 36,36 32,32',
 '32,40 36,36 40,40 36,60 32,64 28,60', '6,61 28,61 32,65 28,69 2,69 0,65',
 '2,39 6,35 10,39 6,59 2,63 0,59', '6,11 10,7 14,11 10,31 6,35 2,31',
 '9,32 31,32 35,36 31,40 9,40 5,36'
];

function Momentary({x,y,label,pressed,change,r=12}:{x:number;y:number;label:string;pressed:boolean;change:(p:boolean)=>void;r?:number}) {
 return <g role="button" aria-label={label} aria-pressed={pressed} tabIndex={0} className="momentary"
 onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);change(true);}}
 onPointerUp={()=>change(false)} onPointerCancel={()=>change(false)}
 onLostPointerCapture={()=>{if(pressed)change(false);}}
 onKeyDown={e=>{if((e.key===' '||e.key==='Enter')&&!e.repeat){e.preventDefault();change(true);}}}
 onKeyUp={e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();change(false);}}}
 onBlur={()=>{if(pressed)change(false);}}>
 <title>{label}</title>
 <rect x={x-r-3} y={y-r-2} width={r*2+6} height={r*2+4} rx="3" fill="url(#metal)" stroke="#c0cdb5"/>
 <circle cx={x} cy={y} r={r} fill={pressed?'#625c3a':'#15221c'} stroke={pressed?'#ffe4a1':'#818b77'} strokeWidth="2"/>
 <text x={x} y={y+3.5} fontSize="9" textAnchor="middle" fill={pressed?'#fff4ce':'#e0e6d2'}>{label.split(' ')[0]}</text>
 </g>;
}

export function Board({info,state,layout:l,physical,control}:Props) {
 const [source,setSource]=useState<string|null>(null);
 const headerClick=(name:string)=>{
  const attached=state.cables.find(c=>c.includes(name));
  if(attached){void physical({action:'disconnect',header:name});setSource(null);return;}
  if(!source){setSource(name);return;}
  if(source===name){setSource(null);return;}
  void physical({action:'connect',a:source,b:name});setSource(null);
 };
 const jumperClick=(name:string)=>{
  const options=info.board.jumpers[name].states;
  void physical({action:'jumper',name,value:options[(options.indexOf(state.jumpers[name])+1)%options.length]});
 };
 return <>
 <div className="board-scroll">
 <svg className="board" viewBox={`0 0 ${l.width} ${l.height}`} xmlns="http://www.w3.org/2000/svg" fontFamily="Arial, sans-serif" aria-label="Interactive ALS LPC1768 evaluation board"
 onKeyDown={e=>{if(e.key==='Escape')setSource(null);}}>
 <title>ALS-SDA-ARMCTXM3-01 · LPC1768 evaluation board</title>
 <BoardArtwork/>
 <g aria-label={`LCD: ${state.lcd.join(' | ')}`}>
  <rect x={l.lcd[0]} y={l.lcd[1]} width={l.lcd[2]} height={l.lcd[3]} rx="3" fill={state.jumpers.JP16==='closed'?'#bdd54e':'#426523'}/>
  {state.jumpers.JP16==='closed'&&state.lcd.map((line,i)=><text key={i} x={l.lcd[0]+12} y={l.lcd[1]+25+i*27} fontFamily="monospace" fontSize="22" textLength={l.lcd[2]-24} lengthAdjust="spacing" fill="#233712" xmlSpace="preserve">{line}</text>)}
 </g>
 <g transform={`translate(${l.seven[0]},${l.seven[1]}) scale(${l.seven[2]/200},${l.seven[3]/72})`} aria-label="Four-digit seven-segment display">
 <rect width="200" height="72" rx="3" fill="#17201a"/>
 {state.segments.map((pattern,d)=><g key={d} transform={`translate(${d*50+3},0)`}>
  <rect x="-2" y="-1" width="48" height="73" rx="2" fill="none" stroke="#94a38c" strokeWidth=".7"/>
  {segmentPolygons.map((p,i)=><polygon key={i} points={p} fill={pattern&(1<<i)?'#ff4b36':'#697567'}/>)}
  <circle cx="44" cy="65" r="3" fill={pattern&128?'#ff4b36':'#697567'}/>
 </g>)}
 </g>
 {l.leds.map(([x,y],i)=><g key={i} aria-label={`LD${i+2} ${state.leds[i]?'on':'off'}`}>
  <title>{`LD${i+2}`}</title>
  {state.leds[i]&&<circle cx={x} cy={y} r="15" fill="#ff8132" opacity=".25"/>}
  <ellipse cx={x} cy={y} rx="7" ry="9" stroke="#b1b78b" fill={state.leds[i]?'#ffca62':'url(#led-lens)'}/>
  <ellipse cx={x-2} cy={y-3} rx="2" ry="3" fill="#fff4c7" opacity={state.leds[i]?'.9':'.2'}/>
 </g>)}
 <g aria-label={`LD10 PWM ${Math.round(state.pwm*100)} percent`}>
  <circle cx={l.ld10[0]} cy={l.ld10[1]} r="13" fill="#ff4a23" opacity={state.pwm*.65}/>
  <circle cx={l.ld10[0]} cy={l.ld10[1]} r="6" fill="url(#led-lens)" stroke="#d1bc8c"/>
  <circle cx={l.ld10[0]} cy={l.ld10[1]} r="5" fill="#ff873f" opacity={state.pwm}/>
  <title>LD10 · {Math.round(state.pwm*100)}%</title>
 </g>
 <Momentary x={l.sw2[0]} y={l.sw2[1]} label="SW2" pressed={state.sw2} change={pressed=>{void physical({action:'switch',pressed});}}/>
 <g role="button" aria-label="SW1 reset" tabIndex={0} className="momentary" onClick={()=>control('reset')}
 onKeyDown={e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();control('reset');}}}>
  <title>SW1</title>
  <rect x={l.sw1[0]-15} y={l.sw1[1]-14} width="30" height="28" rx="3" fill="url(#metal)" stroke="#c0cdb5"/>
  <circle cx={l.sw1[0]} cy={l.sw1[1]} r="12" fill="#15221c" stroke="#818b77" strokeWidth="2"/>
  <text x={l.sw1[0]} y={l.sw1[1]+3.5} textAnchor="middle" fill="#e0e6d2" fontSize="9">RST</text>
 </g>
 {Array.from({length:16},(_,k)=>{
  const x=l.keypad.origin[0]+(k%4)*l.keypad.step[0],y=l.keypad.origin[1]+Math.floor(k/4)*l.keypad.step[1];
  return <g key={k}>
   <rect x={x-18} y={y-16} width="36" height="32" rx="3" fill="none" stroke="#d7e7cf" strokeWidth=".8"/>
   <Momentary x={x} y={y} pressed={state.keys.includes(k)}
    label={`${k.toString(16).toUpperCase()} SW${k+3} row ${Math.floor(k/4)+1} column ${k%4+1}`}
    change={pressed=>{void physical({action:'key',key:k,pressed});}}/>
   <text x={x} y={y+20} textAnchor="middle" fill="#d7e7cf" fontSize="7" pointerEvents="none">SW{k+3}</text>
  </g>;
 })}
 {/* Ten individual conductor paths and a red pin-1 stripe. */}
 {state.cables.map(([a,b],idx)=>{
  const [x1,y1]=l.headers[a], [x2,y2]=l.headers[b];
  const bend=Math.max(65,Math.abs(y2-y1)*.4);
  const verticalA=l.headerOrientations[a]==='vertical',verticalB=l.headerOrientations[b]==='vertical';
  const path=(o:number)=>{
   const ax=x1+(verticalA?0:o),ay=y1+(verticalA?o:0),bx=x2+(verticalB?0:o),by=y2+(verticalB?o:0);
   const acx=ax+(verticalA?(x1<l.width/2?-bend:bend):0),acy=ay-(verticalA?0:bend);
   const bcx=bx+(verticalB?(x2<l.width/2?-bend:bend):0),bcy=by-(verticalB?0:bend);
   return `M ${ax} ${ay} C ${acx} ${acy}, ${bcx} ${bcy}, ${bx} ${by}`;
  };
  return <g key={`${a}-${b}`} className="cable" role="button" aria-label={`Disconnect ${a} to ${b}`} tabIndex={0}
   onClick={()=>{void physical({action:'disconnect',header:a});}}
   onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();void physical({action:'disconnect',header:a});}}}>
   <title>{a} ↔ {b}</title>
   <path d={path(0)} stroke="#101e1b" strokeWidth="29" fill="none" opacity=".4"/>
   {Array.from({length:10},(_,i)=><path key={i} d={path((i-4.5)*2.4)} fill="none" stroke={i===0?'#d9434e':i%2?'#bfc4c4':'#e0e1de'} strokeWidth="2.6"/>)}
   <path d={path(0)} stroke="transparent" strokeWidth="34" fill="none"/>
   <text x={(x1+x2)/2} y={(y1+y2)/2-bend*.6-12} className="cable-number">FRC {idx+1}</text>
  </g>;
 })}
 {Object.entries(l.headers).map(([name,[x,y]])=>{
  const attached=state.cables.some(c=>c.includes(name));
  const selected=source===name;
  return <g key={name} role="button" aria-label={`Header ${name}`} aria-pressed={attached} tabIndex={0}
   className={`header-target ${selected?'selected':''}`}
   onClick={()=>headerClick(name)}
   onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();headerClick(name);}}}>
   <title>{name}</title>
   <rect x={x-(l.headerOrientations[name]==='vertical'?19:40)} y={y-(l.headerOrientations[name]==='vertical'?40:19)} width={l.headerOrientations[name]==='vertical'?38:80} height={l.headerOrientations[name]==='vertical'?80:38} rx="3" fill={selected?'#645328':attached?'#194b39':'#101a16'} stroke={selected?'#ffdf8e':attached?'#91d3ac':'#a7b49c'} strokeWidth="2"/>
   <g transform={`translate(${x} ${y})${l.headerOrientations[name]==='vertical'?' rotate(90)':''}`}>
    <rect x="-34" y="-13" width="68" height="26" fill="#060d09" stroke="#3a4739"/>
    {Array.from({length:10},(_,p)=><g key={p}>
     <rect x={-26+Math.floor(p/2)*12} y={-7+(p%2)*10} width="5" height="5" fill="#9b9471"/>
     <rect x={-24.5+Math.floor(p/2)*12} y={-5.5+(p%2)*10} width="2" height="2" fill="#11180d"/>
    </g>)}
    <path d="M-32-18l5-6 5 6z" fill="#ead9a0"/>
   </g>
   <text x={x} y={y-(l.headerOrientations[name]==='vertical'?46:26)} textAnchor="middle" fill="#f0f2d9" fontSize="12" fontWeight="bold" paintOrder="stroke" stroke="#064d40" strokeWidth="3">{name}</text>
  </g>;
 })}
 {Object.entries(l.jumpers).map(([name,[x,y]])=>{
  const v=state.jumpers[name],pinCount=info.board.jumpers[name].pinCount??physicalJumpers[name]?.pinCount;
  return <g key={name} role="button" aria-label={`Jumper ${name} ${v}`} tabIndex={0} className="jumper-target"
   onClick={()=>jumperClick(name)}
   onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();jumperClick(name);}}}>
   <title>{name} · {v}</title>
   <JumperBody x={x} y={y} name={name} pinCount={pinCount===3?3:2} value={v} labelAbove={name==='JP18'||name==='JP16'}/>
  </g>;
 })}
 {Object.entries(l.pots).map(([ch,[x,y]])=><g key={ch}>
  <title>{ch==='4'?'POT4':'POT1'}</title>
  <rect x={x-17} y={y-17} width="34" height="34" rx="3" fill="#156a91" stroke="#b5d2b9"/>
  <circle cx={x} cy={y} r="13" fill="url(#metal)" stroke="#e6edcf" strokeWidth="2"/>
  <line x1={x} y1={y} x2={x+10*Math.cos((state.pots[ch]/3.3*270-225)*Math.PI/180)}
   y2={y+10*Math.sin((state.pots[ch]/3.3*270-225)*Math.PI/180)} stroke="#163d50" strokeWidth="4"/>
 </g>)}
 </svg>
 </div>
 <div className="pots">
 {[4,5].map(channel=><label key={channel}>
  <span>{channel===4?'POT4':'POT1'}</span>
  <input aria-label={channel===4?'POT4 voltage':'POT1 voltage'} type="range" min="0" max="3.3" step=".01" value={state.pots[channel]}
   onChange={e=>{void physical({action:'pot',channel,voltage:Number(e.target.value)});}}/>
  <output>{state.pots[channel].toFixed(2)} V</output>
 </label>)}
 <span className="pwm-readout">LD10 <strong>{Math.round(state.pwm*100)}%</strong></span>
 </div>
 </>;
}
