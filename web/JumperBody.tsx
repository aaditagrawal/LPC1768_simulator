import {useState} from 'react';

type Props={x:number;y:number;name:string;pinCount:2|3;value?:string;labelAbove?:boolean};

/** Physical header geometry is independent of how many simulation states it has. */
export function JumperBody({x,y,name,pinCount,value='open',labelAbove=false}:Props) {
 const first=-(pinCount-1)*6,width=pinCount*12+8;
 const left=value==='2-3'?first+12:first;
 return <g transform={`translate(${x} ${y})`}>
  <rect className="jumper-hit-area" x={-width/2-4} y={labelAbove?-27:-14} width={width+8} height={labelAbove?49:48} rx="3" fill="transparent"/>
  <rect x={-width/2} y="-10" width={width} height="20" rx="2" fill="#14271e" stroke="#b4c49e"/>
  {Array.from({length:pinCount},(_,i)=><g key={i}>
   <rect data-pin={i+1} x={first+i*12-2} y="-2" width="4" height="4" fill="#e3cf8b" stroke="#a59059" strokeWidth=".5"/>
   <text x={first+i*12} y="18" textAnchor="middle" fill="#d7e7cf" fontSize="6" pointerEvents="none">{i+1}</text>
  </g>)}
  {value!=='open'&&<g>
   <rect data-shunt={value} x={left-4} y="-7" width="20" height="14" rx="2" fill="#cba64d" stroke="#edda9b"/>
   {[left,left+12].map(p=><rect key={p} x={p-1.5} y="-2" width="3" height="4" rx=".5" fill="#584c2d"/>)}
  </g>}
  <text y={labelAbove?-17:29} textAnchor="middle" fill="#f0f2d9" fontSize="8" paintOrder="stroke" stroke="#064d40" strokeWidth="2" pointerEvents="none">{name}</text>
 </g>;
}

/** Movable physical selector for an interface outside the emulated subset. */
export function PhysicalSelector({x,y,name}:{x:number;y:number;name:string}) {
 const storageKey=`lpc-lab-selector-${name}`;
 const [position,setPosition]=useState(()=>{
  const saved=localStorage.getItem(storageKey);
  return saved==='1-2'||saved==='2-3'?saved:'open';
 });
 const cycle=()=>{
  const next=position==='open'?'1-2':position==='1-2'?'2-3':'open';
  setPosition(next);localStorage.setItem(storageKey,next);
 };
 return <g data-physical-jumper={name} role="button" aria-label={`Jumper ${name} ${position}`}
  tabIndex={0} className="jumper-target" pointerEvents="all" onClick={cycle}
  onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();if(!event.repeat)cycle();}}}>
  <title>{name} · {position}</title>
  <JumperBody x={x} y={y} name={name} pinCount={3} value={position}/>
 </g>;
}
