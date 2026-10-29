import {memo} from 'react';
import {tokenizeC} from './cSyntax';
import './CSource.css';

// React escapes every token; source text is never interpreted as HTML.
export const CSource=memo(function CSource({source}:{source:string}){
 return <code className="c-source">{tokenizeC(source).map(token=>token.kind==='plain'
  ?token.value:<span key={token.start} className={`c-${token.kind}`}>{token.value}</span>)}</code>;
});
