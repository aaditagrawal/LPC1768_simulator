import {useEffect,useState} from 'react';
import {api} from './api';
import {CSource} from './CSource';
import type {Exercise} from './types';
import './ExerciseSolution.css';

interface Props {
 exercise:Exercise;
 compiling:boolean;
 onOpen:(source:string,exercise:Exercise)=>void;
 onDownload:(source:string,name:string)=>void;
}

export function ExerciseSolution({exercise,compiling,onOpen,onDownload}:Props) {
 const [result,setResult]=useState<{id:string;source:string|null;error:string}|null>(null);
 const [attempt,setAttempt]=useState(0);
 useEffect(()=>{
  let active=true;
  setResult(null);
  api<{source:string}>(`/api/examples/${encodeURIComponent(exercise.id)}`)
   .then(value=>{
    if(typeof value.source!=='string')throw new Error('The solution could not be read.');
    if(active)setResult({id:exercise.id,source:value.source,error:''});
   }).catch(error=>{if(active)setResult({id:exercise.id,source:null,error:(error as Error).message});});
  return()=>{active=false;};
 },[exercise.id,attempt]);
 const current=result?.id===exercise.id?result:null;
 const source=current?.source??null;
 return <section className="exercise-solution panel" aria-labelledby="solution-heading">
  <div className="panel-heading"><div><h3 id="solution-heading">Solution code</h3><p className="solution-exercise">{exercise.title}</p></div>
   <div className="solution-actions">
    <button disabled={source===null} onClick={()=>{if(source!==null)onDownload(source,`${exercise.id}.c`);}}>Download C</button>
    <button disabled={source===null||compiling} onClick={()=>{if(source!==null&&!compiling)onOpen(source,exercise);}}>Open in IDE</button>
   </div>
  </div>
  <p className="solution-note">Open in IDE replaces your current C source.</p>
  {!current&&<p className="solution-message" role="status">Loading solution…</p>}
  {current?.error&&<div className="solution-message"><p role="alert" className="error">{current.error}</p><button onClick={()=>setAttempt(n=>n+1)}>Retry</button></div>}
  {source!==null&&<div className="solution-code" tabIndex={0} role="region" aria-label="Read-only solution code">
   <pre className="solution-line-numbers" aria-hidden="true">{Array.from({length:source.split('\n').length},(_,i)=>i+1).join('\n')}</pre>
   <pre aria-label="Solution source"><CSource source={source}/></pre>
  </div>}
 </section>;
}
