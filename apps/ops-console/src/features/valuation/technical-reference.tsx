'use client';
import {useState} from 'react';

/** Full identifiers remain explicitly inspectable/copyable, never a primary label. */
export function TechnicalReference({id,label='Technical ID'}:{id?:string|null;label?:string}){
 const [message,setMessage]=useState('');
 if(!id)return null;
 async function copy(){try{await navigator.clipboard.writeText(id!);setMessage('Copied');}catch{setMessage('Copy unavailable. Select the ID to copy it manually.');}}
 return <details className="pnl-technical-reference"><summary>{label}</summary><code>{id}</code><button type="button" onClick={()=>void copy()}>Copy ID</button><span role="status">{message}</span></details>;
}
export function ReferenceName({id,label,fallback='Name unavailable'}:{id?:string|null;label?:string|null;fallback?:string}){
 // The native disclosure is flow content: callers must not place this inside p/span.
 return <div className="pnl-reference"><span>{label??fallback}</span><TechnicalReference id={id}/></div>;
}
