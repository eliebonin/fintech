'use client';
import {useEffect,useRef,useState} from 'react';
import {browserFetch} from '@/lib/browser-fetch';
import {valuationError} from '@/lib/daily-valuation-request';
import type {Choice} from './types';

type Page={items:Choice[];selected:Choice|null;total:number;limit:number;offset:number};
type Props={kind:'strategies'|'policies'|'currencies';label:string;name:string;value:string;
  initialChoices:Choice[];onChange:(event:{target:{value:string}},choice?:Choice)=>void;
  forCalculation?:boolean;strategyId?:string;required?:boolean;disabled?:boolean;emptyLabel?:string};

/** Search + native select: keyboard semantics remain native, authority stays server-side. */
export function PagedValuationChoice({kind,label,name,value,initialChoices,onChange,forCalculation=false,
  strategyId,required=false,disabled=false,emptyLabel='Select an option'}:Props){
  const [query,setQuery]=useState(''),[items,setItems]=useState<Choice[]>(initialChoices);
  const [selected,setSelected]=useState<Choice|null>(null),[total,setTotal]=useState(initialChoices.length);
  const [end,setEnd]=useState(0),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const [ready,setReady]=useState(false),[revision,setRevision]=useState(0);
  const generation=useRef(0),select=useRef<HTMLSelectElement>(null);
  async function load(offset=0,current=++generation.current){
    setLoading(true);setError('');
    const parameters=new URLSearchParams({kind,q:query,limit:'25',offset:String(offset)});
    if(value)parameters.set('selected_id',value);
    if(strategyId&&kind==='policies')parameters.set('strategy_id',strategyId);
    if(forCalculation)parameters.set('for_calculation','true');
    try{
      const response=await browserFetch(`/api/valuation/option-choices?${parameters}`,{cache:'no-store'});
      const body=await response.json();if(!response.ok)throw valuationError(response,body);
      const page=body as Page;
      if(!Array.isArray(page.items)||!Number.isInteger(page.total))throw new Error('Option search returned an incomplete response.');
      if(current!==generation.current)return;
      setItems(previous=>offset?[...previous,...page.items.filter(item=>!previous.some(old=>old.id===item.id))]:page.items);
      setSelected(page.selected);setTotal(page.total);setEnd(page.offset+page.items.length);setReady(true);
    }catch(cause){if(current===generation.current){setError(cause instanceof Error?cause.message:'Options could not be loaded.');setReady(false);}}
    finally{if(current===generation.current)setLoading(false);}
  }
  useEffect(()=>{
    const current=++generation.current;setReady(false);
    const timer=setTimeout(()=>void load(0,current),250);
    return()=>{clearTimeout(timer);generation.current++;};
  },[kind,query,value,strategyId,forCalculation,revision]);
  const chosen=selected?.id===value?selected:items.find(item=>item.id===value)??initialChoices.find(item=>item.id===value);
  const choices=chosen&&!items.some(item=>item.id===chosen.id)?[chosen,...items]:items;
  const unavailable=Boolean(value&&ready&&!selected&&!items.some(item=>item.id===value));
  useEffect(()=>{select.current?.setCustomValidity((error&&(Boolean(value)||required))||unavailable?'Choose an available option, or retry the search.':
    !ready&&(Boolean(value)||required)?'Wait for the available options to be checked.':'');},[error,unavailable,value,required,ready]);
  return <div className="pnl-paged-choice">
    <label>Search {label.toLowerCase()}<input type="search" value={query} maxLength={120} disabled={disabled}
      onChange={event=>setQuery(event.target.value)} placeholder={`Search ${label.toLowerCase()}`}/></label>
    <label>{label}<select ref={select} name={name} value={value} required={required} disabled={disabled} aria-busy={loading}
      onChange={event=>onChange(event,choices.find(item=>item.id===event.target.value))}>
      <option value="">{emptyLabel}</option>
      {choices.map(choice=><option key={choice.id} value={choice.id} disabled={unavailable&&choice.id===value}>
        {choice.label}{unavailable&&choice.id===value?' — no longer available':''}</option>)}
    </select></label>
    {loading?<small role="status">Searching…</small>:ready?<small>{total} matching · {items.length} loaded</small>:null}
    {error?<p role="alert">{error} <button type="button" disabled={disabled} onClick={()=>setRevision(n=>n+1)}>Retry search</button></p>:null}
    {ready&&end<total?<button type="button" disabled={disabled||loading} onClick={()=>void load(end)}>Load more {label.toLowerCase()}</button>:null}
    {unavailable?<p role="alert">The selected {label.toLowerCase()} is no longer available for this action.</p>:null}
  </div>;
}
