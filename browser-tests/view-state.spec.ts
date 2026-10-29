import {test,expect} from '@playwright/test';
import type {State} from '../web/types';
import {reconcileViewState} from '../web/viewState';

const snapshot=():State=>({
 status:'running',loaded:true,firmwareName:'program.c',diagnostics:'Build succeeded',error:null,
 leds:Array(8).fill(false),lcd:[' '.repeat(16),' '.repeat(16)],segments:[0,0,0,0],pwm:0,
 cables:[['CNA','CNA1']],jumpers:{JP4:'open',JP5:'closed',JP16:'closed'},pots:{4:1.65,5:1.65},
 keys:[],sw2:false,sw2Pin:10,ticks:1,gpioEvents:0,lcdEdges:0,interrupts:0,pc:'0x00000100',
 warnings:[],gpio:[{direction:'0x00000010',latch:'0x00000000'}]
});

test('internal execution activity reuses the visible snapshot instead of scheduling another render',()=>{
 const previous=snapshot(),next=snapshot();
 Object.assign(next,{ticks:100000,gpioEvents:500,lcdEdges:200,interrupts:50,pc:'0x00000200',
  gpio:[{direction:'0x00000010',latch:'0x00000010'}],sw2Pin:12});
 expect(reconcileViewState(previous,next)).toBe(previous);
});

test('every visible output, control, diagnostic and runtime status change reaches the view',()=>{
 const changes:Partial<State>[]=[
  {status:'paused'},{loaded:false},{firmwareName:'uploaded.hex'},{diagnostics:'Compiler warning'},
  {error:'CPU fault'},{leds:[true,false,false,false,false,false,false,false]},
  {lcd:['Hello LCD','Second line']},{segments:[0x3f,6,0x5b,0x4f]},
  {pwm:0.00001},{cables:[['CND','CNAD']]},{cables:[['CNA','CNA2']]},{cables:[]},
  {jumpers:{JP4:'open',JP5:'open',JP16:'closed'}},{jumpers:{JP16:'closed'}},
  {pots:{4:1.65001,5:1.65}},{keys:[15]},{sw2:true},{warnings:['Cable conflict']}
 ];
 for(const change of changes){
  const previous=snapshot(),next={...snapshot(),...change};
  const result=reconcileViewState(previous,next);
  expect(result,JSON.stringify(change)).not.toBe(previous);
  expect(result).toMatchObject(change);
 }
});

test('fresh JSON arrays and records with equal values keep the existing view',()=>{
 const previous=snapshot();
 expect(reconcileViewState(previous,JSON.parse(JSON.stringify(previous)))).toBe(previous);
});

test('initial snapshots and subsequent changes are retained without mutating either input',()=>{
 const previous=snapshot(),before=JSON.stringify(previous),next=snapshot();
 next.leds[7]=true;next.keys=[0,15];
 expect(reconcileViewState(null,previous)).toMatchObject({status:'running',sw2:false});
 const result=reconcileViewState(previous,next);
 expect(result.leds[7]).toBe(true);expect(result.keys).toEqual([0,15]);
 expect(JSON.stringify(previous)).toBe(before);
 expect(next.leds[7]).toBe(true);
});
