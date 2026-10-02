'use client';
import {useRef,useState} from 'react';
import Link from 'next/link';
import type {components} from 'api-contracts';
import {bffGet} from '@/lib/browser-api-client';
export type FutureFamily=components['schemas']['FutureFamilyView'];
export function FutureFamilySelector({onSelect,disabled=false}:{onSelect:(family:FutureFamily)=>void;disabled?:boolean}) {
  const [query,setQuery]=useState(''),[rows,setRows]=useState<FutureFamily[]>([]),[total,setTotal]=useState(0),[offset,setOffset]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [searched,setSearched]=useState(false);
  const serial=useRef(0);
  async function search(start=0){const n=++serial.current;setBusy(true);setError('');try{const response=await bffGet<components['schemas']['FutureFamilySearchResponse']>(`/api/instruments/future-families?${new URLSearchParams({q:query,limit:'20',offset:String(start)})}`);if(n===serial.current){setSearched(true);setRows(response.data);setTotal(response.meta.total??0);setOffset(start);}}catch(e){if(n===serial.current)setError(e instanceof Error?e.message:'Family search failed.');}finally{if(n===serial.current)setBusy(false);}}
  return <section className="detail-card"><h2>Approved futures family</h2><p>Select the contract family first. Its underlying and currency are inherited; this does not select an expiry.</p><label>Search families<input value={query} maxLength={250} disabled={disabled} onChange={e=>{serial.current++;setSearched(false);setQuery(e.target.value);setRows([]);setTotal(0);setBusy(false);}}/></label><button type="button" disabled={disabled||busy} onClick={()=>search()}>{busy?'Searching…':'Find families'}</button> <Link href="/instruments/future-families">Create or browse families</Link>{error?<p role="alert">{error}</p>:null}<ul className="ticket-options">{rows.map(r=><li key={r.familyId}><button type="button" disabled={disabled||busy} onClick={()=>onSelect(r)}>{r.canonicalName} · {r.familyCode} · {r.underlyingName} · {r.currency}</button></li>)}</ul><p>{searched?`${total} approved families match.`:'Search to browse approved families.'} Pending requests appear in Operations.</p>{total>20?<div><button type="button" disabled={disabled||busy||offset===0} onClick={()=>search(offset-20)}>Previous</button><button type="button" disabled={disabled||busy||offset+20>=total} onClick={()=>search(offset+20)}>Next</button></div>:null}</section>;
}
