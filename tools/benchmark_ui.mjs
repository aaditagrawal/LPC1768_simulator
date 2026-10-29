// Run only against a disposable server: this loads firmware and changes wiring.
// LPC_LAB_URL=http://127.0.0.1:8879 node tools/benchmark_ui.mjs baseline
import {chromium} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';

const base=process.env.LPC_LAB_URL;
if(!base||!/^http:\/\/127\.0\.0\.1:8879\/?$/.test(base)){
 throw new Error('Set LPC_LAB_URL=http://127.0.0.1:8879; never benchmark the practice server.');
}
const label=process.argv[2]||'current';
if(!/^[a-z0-9-]+$/i.test(label))throw new Error('Use a simple report label.');
async function api(path,data){
 const response=await fetch(new URL(path,base),data?{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(data)}:{});
 const result=await response.json();
 if(!response.ok)throw new Error(JSON.stringify(result));
 return result;
}
const browser=await chromium.launch({headless:true}),results=[];
try{
 await api('/api/control',{action:'stop'});
 for(const [header] of (await api('/api/state')).cables){
  await api('/api/physical',{action:'disconnect',header});
 }
 await api('/api/compile',{source:`#include <LPC17xx.h>
int main(void){SystemCoreClockUpdate();LPC_PINCON->PINSEL0 &= ~(3U<<8);LPC_GPIO0->FIODIR|=16;
LPC_SC->PCONP|=2;LPC_SC->PCLKSEL0 &= ~(3U<<2);LPC_TIM0->TCR=2;
LPC_TIM0->PR=SystemCoreClock/4/1000-1;LPC_TIM0->MR0=250;LPC_TIM0->MCR=3;LPC_TIM0->TCR=1;
while(1){LPC_GPIO0->FIOSET=16;while(!(LPC_TIM0->IR&1));LPC_TIM0->IR=1;
LPC_GPIO0->FIOCLR=16;while(!(LPC_TIM0->IR&1));LPC_TIM0->IR=1;}}`});
 await api('/api/physical',{action:'connect',a:'CNA',b:'CNA1'});
 await api('/api/control',{action:'run'});
 for(let trial=1;trial<=3;trial++){
  const page=await browser.newPage({viewport:{width:1366,height:768}});
  await page.goto(base+'/#board');await page.getByLabel('Board zoom').waitFor();
  await page.waitForTimeout(1000);
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Performance.enable',{timeDomain:'threadTicks'});
  const metrics=async()=>Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
  await page.evaluate(()=>{
   window.benchEdges=[];
   const observer=new MutationObserver(()=>window.benchEdges.push(performance.now()));
   observer.observe(document.querySelector('g[aria-label^="LD2 "]'),{attributes:true,attributeFilter:['aria-label']});
  });
  let requests=0;page.on('response',r=>{if(r.url().endsWith('/api/state'))requests++;});
  const before=await metrics(),started=performance.now();
  await page.waitForTimeout(8000);
  const seconds=(performance.now()-started)/1000,after=await metrics();
  const edges=await page.evaluate(()=>window.benchEdges);
  const gaps=edges.slice(1).map((t,i)=>t-edges[i]).sort((a,b)=>a-b);
  const row={trial,seconds,requestsPerSecond:requests/seconds,
   browserMainThreadPercent:(after.TaskDuration-before.TaskDuration)/seconds*100,
   visibleIntervalMs:{min:gaps[0],median:gaps[Math.floor(gaps.length/2)],max:gaps.at(-1)}};
  results.push(row);console.log(JSON.stringify(row));await page.close();
 }
}finally{
 await browser.close();
 await api('/api/control',{action:'pause'});
}
mkdirSync('build',{recursive:true});
writeFileSync(`build/ui-benchmark-${label}.json`,JSON.stringify(results,null,2));
