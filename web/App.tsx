import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {api} from './api';
import {Board} from './Board';
import {ExerciseSolution} from './ExerciseSolution';
import type {Info,State,Layout,Exercise} from './types';

const DEFAULT_SOURCE=`#include <LPC17xx.h>

int main(void)
{
    SystemInit();
    SystemCoreClockUpdate();

    while (1) {
    }
}
`;

type Screen='board'|'ide'|'labs';
const currentScreen=():Screen=>{
 const hash=window.location.hash.slice(1);
 return hash==='ide'||hash==='labs'?hash:'board';
};

export function App() {
 const [info,setInfo]=useState<Info|null>(null),[state,setState]=useState<State|null>(null),[layout,setLayout]=useState<Layout|null>(null);
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [loadingHex,setLoadingHex]=useState(false);
 const [buildError,setBuildError]=useState('');
 const [exercise,setExercise]=useState(()=>localStorage.getItem('lpc-lab-exercise')||'lab7_sequence');
 const [source,setSource]=useState(()=>localStorage.getItem('lpc-lab-source')??DEFAULT_SOURCE);
 const [dirty,setDirty]=useState(true),[message,setMessage]=useState('');
 const [zoom,setZoom]=useState(100),[screen,setScreen]=useState<Screen>(currentScreen);
 const [hex,setHex]=useState<string|null>(null),[firmwareKind,setFirmwareKind]=useState<'c'|'hex'>('c');
 const queue=useRef<Promise<void>>(Promise.resolve()),revision=useRef(0),fileInput=useRef<HTMLInputElement>(null);
 const requestNumber=useRef(0),latestSource=useRef(source),previousScreen=useRef(screen);
 const firmwareBusy=useRef(false),selectedExercise=useRef(exercise);
 selectedExercise.current=exercise;
 const sourceEditor=useRef<HTMLTextAreaElement>(null),lineNumbers=useRef<HTMLPreElement>(null);
 const editorPosition=useRef({start:0,end:0,top:0,left:0});
 const attachSourceEditor=useCallback((editor:HTMLTextAreaElement|null)=>{
  const previous=sourceEditor.current;
  if(previous)editorPosition.current={start:previous.selectionStart,end:previous.selectionEnd,top:previous.scrollTop,left:previous.scrollLeft};
  sourceEditor.current=editor;
  if(editor){
   const saved=editorPosition.current;
   editor.setSelectionRange(saved.start,saved.end);
   editor.scrollTop=saved.top;editor.scrollLeft=saved.left;
  }
 },[]);
 const syncEditorScroll=()=>{
  if(sourceEditor.current&&lineNumbers.current)lineNumbers.current.style.transform=`translateY(-${sourceEditor.current.scrollTop}px)`;
 };
 useLayoutEffect(syncEditorScroll,[source,screen]);

 useEffect(()=>{
  let active=true;
  Promise.all([api<Info>('/api/info'),api<State>('/api/state'),api<Layout>('/board/layout.json')])
   .then(([i,s,l])=>{if(active){setInfo(i);setState(s);setLayout(l);}}).catch(e=>{if(active)setError(String(e.message));});
  return()=>{active=false;};
 },[]);
 useEffect(()=>{localStorage.setItem('lpc-lab-source',source);},[source]);
 useEffect(()=>{localStorage.setItem('lpc-lab-exercise',exercise);},[exercise]);
 useEffect(()=>{
  document.title=`LPC1768 · ${screen==='board'?'Board':screen==='ide'?'IDE':'Lab exercises'}`;
 },[screen]);
 useEffect(()=>{
  const navigate=()=>{
   const next=currentScreen();
   if(previousScreen.current==='board'&&next!=='board')void physical({action:'release-inputs'});
   previousScreen.current=next;setScreen(next);
  };
  window.addEventListener('hashchange',navigate);
  return()=>window.removeEventListener('hashchange',navigate);
 },[]);
 useEffect(()=>{
  let cancelled=false,polling=false;
  const timer=setInterval(async()=>{
   if(polling)return;
   polling=true;
   const rev=revision.current;
   try {const s=await api<State>('/api/state');if(!cancelled&&rev===revision.current)setState(s);}
   catch(e){if(!cancelled)setError((e as Error).message);}
   finally{polling=false;}
  },150);
  const release=()=>{void physical({action:'release-inputs'});};
  window.addEventListener('blur',release);
  return()=>{cancelled=true;clearInterval(timer);window.removeEventListener('blur',release);};
 },[]);

 const physical=(data:unknown):Promise<void>=>{
  revision.current++;
  queue.current=queue.current.then(async()=>{
   try{setState(await api<State>('/api/physical',data));setError('');}
   catch(e){setError((e as Error).message);}
  });
  return queue.current;
 };
 const control=async(action:string)=>{
  revision.current++;
  try{await queue.current;setState(await api<State>('/api/control',{action}));setError('');}
  catch(e){setError((e as Error).message);}
 };
 const compile=async()=>{
  if(firmwareBusy.current)return;
  firmwareBusy.current=true;
  setBusy(true);setError('');setBuildError('');setMessage('Compiling…');
  requestNumber.current++;
  revision.current++;
  const code=source;
  try{
   const result=await api<{state:State;hex:string;diagnostics:string}>('/api/compile',{source:code});
   setState(result.state);setHex(result.hex);setDirty(latestSource.current!==code);setFirmwareKind('c');setMessage(result.diagnostics);
  }catch(e){setBuildError((e as Error).message);setMessage('Compilation failed.');}
  finally{firmwareBusy.current=false;setBusy(false);}
 };
 const upload=async(file:File)=>{
  if(firmwareBusy.current)return;
  const number=++requestNumber.current;
  setError('');setBuildError('');
  try{
   if(file.size>3_000_000)throw new Error('File is too large (maximum 3 MB).');
   const text=await file.text();
   if(number!==requestNumber.current)return;
   if(/\.hex$/i.test(file.name)){
    firmwareBusy.current=true;setBusy(true);setLoadingHex(true);
    try {
    revision.current++;
    const uploaded=await api<State>('/api/firmware',{hex:text,name:file.name});
    if(number!==requestNumber.current)return;
    setState(uploaded);
    setHex(text);setFirmwareKind('hex');setDirty(false);setMessage(`Loaded ${file.name}.`);
    } finally {
     firmwareBusy.current=false;setBusy(false);setLoadingHex(false);
    }
   }else if(/\.c$/i.test(file.name)){
    latestSource.current=text;setSource(text);setDirty(true);setFirmwareKind('c');setMessage(`Opened ${file.name}.`);
   }else throw new Error('Choose a .c or .hex file.');
  }catch(e){if(number===requestNumber.current)setError((e as Error).message);}
 };
 const openSolution=(code:string,selected:Exercise)=>{
  if(firmwareBusy.current||selected.id!==selectedExercise.current)return;
  requestNumber.current++;
  editorPosition.current={start:0,end:0,top:0,left:0};
  latestSource.current=code;setSource(code);setDirty(true);setFirmwareKind('c');
  setError('');setBuildError('');setMessage(`Opened ${selected.title} solution. Compile C to load it.`);
  window.location.hash='ide';
 };
 const download=(content:string,name:string)=>{
  const url=URL.createObjectURL(new Blob([content],{type:'text/plain'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);
 };

 if(!info||!state||!layout)return <main className="loading"><h1>LPC1768 Virtual Lab</h1><p>{error||'Connecting…'}</p></main>;
 const spec=info.exercises.find(e=>e.id===exercise);
 const running=state.status==='running',runnable=state.loaded&&!busy&&!dirty&&state.status!=='error';
 const runtimeControls=<div className="runtime-controls">
  <button className="run" disabled={!runnable||running} onClick={()=>{void control(state.status==='paused'?'resume':'run');}}>{state.status==='paused'?'▶ Resume':'▶ Run'}</button>
  <button disabled={!running||busy} onClick={()=>{void control('pause');}}>Ⅱ Pause</button>
  <button disabled={!state.loaded||busy} onClick={()=>{void control('stop');}}>■ Stop</button>
  <button disabled={busy} onClick={()=>{void control('reset');}}>↺ Reset</button>
 </div>;
 const diagnosticText=state.error||message||(state.loaded?state.diagnostics:'');
 const diagnostics=(error||buildError||diagnosticText)?<div className="diagnostics" aria-label="Compiler and runtime messages">
  {error&&<pre role="alert" className="error">{error}</pre>}
  {buildError&&<pre role="alert" className="error">{buildError}</pre>}
  {diagnosticText&&<pre role="status">{diagnosticText}</pre>}
 </div>:null;

 return <div className="app-shell">
  <header className="app-header">
   <div className="identity"><div className="chip-logo">M3</div><h1>LPC1768 <span>Virtual Lab</span></h1></div>
   <div className="engine-state"><span className={`dot ${running?'green':state.status==='error'?'red':''}`}/><span>{state.status.toUpperCase()}</span></div>
  </header>
  <nav className="screen-nav" aria-label="Workspace">
   <a href="#board" aria-current={screen==='board'?'page':undefined}>Board</a>
   <a href="#ide" aria-current={screen==='ide'?'page':undefined}>IDE</a>
   <a href="#labs" aria-current={screen==='labs'?'page':undefined}>Lab exercises</a>
  </nav>
  <main className={`workspace ${screen}-screen`}>
   {screen==='board'&&<section className="board-panel panel" aria-label="Virtual board panel">
    <div className="panel-heading"><h2>Virtual evaluation board</h2>
     <label className="zoom-control">Zoom <input aria-label="Board zoom" type="range" min="100" max="180" step="10" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></label>
    </div>
    {runtimeControls}
    <div className="zoom-container" style={{'--board-zoom':zoom/100} as React.CSSProperties}>
     <Board info={info} state={state} layout={layout} physical={physical} control={action=>{void control(action);}}/>
    </div>
    <div className="board-connections">
     <div className="cable-tags" aria-label="Connected cables">{state.cables.map(([a,b])=><button key={a} onClick={()=>{void physical({action:'disconnect',header:a});}} aria-label={`Disconnect cable ${a} to ${b}`}>{a} ↔ {b} <span>×</span></button>)}</div>
     <div className="jumper-tray">
      {Object.entries(info.board.jumpers).map(([name,j])=><label key={name}><span>{name}</span>
       <select aria-label={`${name} position`} value={state.jumpers[name]} onChange={e=>{void physical({action:'jumper',name,value:e.target.value});}}>
        {j.states.map(s=><option key={s} value={s}>{s==='open'?'Open':s==='closed'?'Closed':`Pins ${s}`}</option>)}
       </select></label>)}
     </div>
    </div>
    {state.warnings.length>0&&<div className="warning" role="status">{state.warnings.map(w=><p key={w}>{w}</p>)}</div>}
    {diagnostics}
   </section>}
   {screen==='ide'&&<section className="ide-panel panel" aria-label="IDE">
    <div className="panel-heading"><h2>IDE</h2><span className="current-exercise">{spec?.title}</span></div>
    <div className="editor-toolbar"><span>program.c</span><span>{firmwareKind==='hex'?'HEX firmware loaded':dirty?'C source · compile pending':'C source · compiled'}</span></div>
    <div className="code-editor-shell">
     <div className="line-number-gutter" aria-hidden="true"><pre ref={lineNumbers}>{Array.from({length:source.split('\n').length},(_,i)=>i+1).join('\n')}</pre></div>
     <textarea ref={attachSourceEditor} aria-label="Embedded C editor" className="code-editor" value={source} spellCheck={false} disabled={busy} wrap="off" onScroll={syncEditorScroll}
      onChange={e=>{latestSource.current=e.target.value;setSource(e.target.value);setDirty(true);setFirmwareKind('c');}}
      onKeyDown={e=>{if(e.key==='Tab'){e.preventDefault();const editor=e.currentTarget,start=editor.selectionStart,end=editor.selectionEnd;const next=source.slice(0,start)+'    '+source.slice(end);latestSource.current=next;setSource(next);setDirty(true);setFirmwareKind('c');requestAnimationFrame(()=>editor.setSelectionRange(start+4,start+4));}}}/>
    </div>
    <div className="ide-actions">
     <div className="file-actions"><button onClick={()=>fileInput.current?.click()} disabled={busy}>↑ Open C / HEX</button><button onClick={()=>download(source,'program.c')}>↓ C</button><button disabled={!hex} onClick={()=>hex&&download(hex,'firmware.hex')}>↓ HEX</button>
      <input ref={fileInput} type="file" accept=".c,.hex" hidden disabled={busy} aria-label="Upload C or HEX" onChange={e=>{const f=e.target.files?.[0];if(f)void upload(f);e.target.value='';}}/></div>
     <button className="compile" disabled={busy||!info.compiler.available} onClick={()=>{void compile();}}>{busy?(loadingHex?'Loading HEX…':'Compiling…'):'Compile C'}</button>
     {runtimeControls}
    </div>
    {diagnostics}
   </section>}
   {screen==='labs'&&<section className="labs-panel" aria-label="Lab exercises">
    <div className="panel-heading"><h2>Lab exercises</h2></div>
    {spec&&<ExerciseSolution exercise={spec} compiling={busy} onOpen={openSolution} onDownload={download}/>}
    {[6,7,8,9,10,11].map(lab=><section className="lab-group" key={lab} aria-labelledby={`lab-${lab}`}>
     <h3 id={`lab-${lab}`}>Lab {lab}{lab===11?' · PWM':''}</h3>
     <div className="exercise-grid">{info.exercises.filter(e=>e.lab===lab).map(e=><button key={e.id} className="exercise-card" aria-pressed={exercise===e.id} onClick={()=>setExercise(e.id)}>{e.title}</button>)}</div>
    </section>)}
    {error&&<p role="alert" className="error">{error}</p>}
   </section>}
  </main>
 </div>;
}
