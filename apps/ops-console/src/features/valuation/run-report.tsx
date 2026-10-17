'use client';
import {PagedValuationChoice} from './paged-choice';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {valuationError} from '@/lib/daily-valuation-request';
import {displayAmount,displayTime} from './presentation';
import type {Attempt,Choice} from './types';

/** Calculation completion is not financial approval. Never infer publication. */
export function runStatus(run:Pick<Attempt,'status'|'batch_status'|'publication_review_mode'|'source_health_status'>):string{
 if(run.status==='RUNNING')return 'Running · Calculation in progress';
 if(run.status==='FAILED')return 'Failed · No result';
 const active=run.batch_status==='PUBLISHED'||run.batch_status==='STAGED';
 const warning=!active?'':run.source_health_status==='REASSESSMENT_REQUIRED'?' · Reassessment required':run.source_health_status==='UNKNOWN_LEGACY'?' · Legacy source proof unavailable':'';
 const publication=({STAGED:'Staged — not published',PUBLISHED:'Published',SUPERSEDED:'Superseded',CANCELLED:'Cancelled — not published'} as Record<string,string>)[run.batch_status??''];
 return `${run.status==='COMPLETED'?'Completed':run.status} · ${publication??'No result recorded'}${warning}${run.batch_status==='PUBLISHED'&&run.publication_review_mode==='SELF_REVIEWED'?' · Self-reviewed':''}`;
}
type Filters={strategy_id:string;from_date:string;to_date:string;calculation_status:string;publication_status:string};
function recentDates(){const today=new Date();const to=today.toISOString().slice(0,10);today.setUTCDate(today.getUTCDate()-13);return{from_date:today.toISOString().slice(0,10),to_date:to};}

/** Filters and totals are authoritative server results, never a filtered local page. */
export function RunReport({mode,strategies,policies,currencies,busy,revision,onOpen}:{mode:'results'|'history';strategies:Choice[];policies:Choice[];currencies:Choice[];busy:boolean;revision:number;onOpen:(id:string)=>unknown}){
 const [filters,setFilters]=useState<Filters>({strategy_id:'',...recentDates(),calculation_status:'',publication_status:''});
 const [items,setItems]=useState<Attempt[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(0);
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[searched,setSearched]=useState(false);
 const generation=useRef(0),applied=useRef<Filters|null>(null);
 async function load(selection:Filters,offset=0){
  if(mode==='results'&&!selection.strategy_id){setError('Select a strategy to find valuation results.');return;}
  if(selection.from_date&&selection.to_date&&selection.from_date>selection.to_date){setError('From valuation date must not follow To valuation date.');return;}
  const current=++generation.current;setLoading(true);setError('');setItems([]);setSearched(false);applied.current={...selection};
  const query=new URLSearchParams({limit:'25',offset:String(offset*25)});
  for(const [key,value] of Object.entries(selection))if(value)query.set(key,value);
  if(mode==='results')query.set('results_only','true');
  try{
   const response=await fetch(`/api/valuation/attempts?${query}`,{cache:'no-store'});const body=await response.json();
   if(!response.ok)throw valuationError(response,body);
   if(current===generation.current){setItems(body.items);setTotal(body.total);setPage(offset);setSearched(true);}
  }catch(e){if(current===generation.current)setError((e as Error).message);}
  finally{if(current===generation.current)setLoading(false);}
 }
 useEffect(()=>{if(applied.current)void load(applied.current);else if(mode==='history')void load(filters);return()=>{generation.current++;};},[revision]);
 function change(name:keyof Filters,value:string){generation.current++;setFilters(current=>({...current,[name]:value}));setItems([]);setTotal(0);setPage(0);setSearched(false);setLoading(false);setError('');applied.current=null;}
 function preset(single=false){generation.current++;const dates=recentDates();setFilters(current=>({...current,...(single?{from_date:current.to_date||dates.to_date,to_date:current.to_date||dates.to_date}:dates)}));setItems([]);setTotal(0);setPage(0);setSearched(false);setLoading(false);setError('');applied.current=null;}
 async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();await load(filters);}
 return <section className="pnl-surface pnl-run-report" aria-label={mode==='results'?'Find valuation results':'Run history report'}>
  <h2>{mode==='results'?'Find valuation results':'Run history'}</h2>
  <p className="pnl-muted">{mode==='results'?'Choose a strategy and valuation dates, then open a recorded result. Failed calculations are available in History.':'Inspect calculation attempts and their logs. Filter dates refer to the closing valuation date, not when the calculation was run.'}</p>
  <form onSubmit={submit} className="pnl-report-filters">
   <PagedValuationChoice kind="strategies" label="Strategy" name="strategy_id" required={mode==='results'} value={filters.strategy_id} disabled={busy} onChange={e=>change('strategy_id',e.target.value)} initialChoices={strategies} emptyLabel={mode==='results'?'Select a strategy':'All readable strategies'}/>
   <label>From valuation date<input type="date" name="from_date" value={filters.from_date} disabled={busy} onChange={e=>change('from_date',e.target.value)}/></label>
   <label>To valuation date<input type="date" name="to_date" value={filters.to_date} disabled={busy} onChange={e=>change('to_date',e.target.value)}/></label>
   {mode==='history'?<label>Calculation status<select name="calculation_status" value={filters.calculation_status} disabled={busy} onChange={e=>change('calculation_status',e.target.value)}><option value="">All calculations</option><option value="RUNNING">Running</option><option value="COMPLETED">Completed</option><option value="FAILED">Failed</option></select></label>:null}
   <label>Publication state<select name="publication_status" value={filters.publication_status} disabled={busy} onChange={e=>change('publication_status',e.target.value)}><option value="">All states</option><option value="STAGED">Staged — not published</option><option value="PUBLISHED">Published</option><option value="SUPERSEDED">Superseded</option><option value="CANCELLED">Cancelled — not published</option></select></label>
   <div className="pnl-report-actions"><button type="submit" disabled={busy||loading}>{loading?'Loading…':mode==='results'?'Find results':'Apply filters'}</button><button type="button" disabled={busy} onClick={()=>preset()}>Last 14 days</button><button type="button" disabled={busy} onClick={()=>preset(true)}>Single day</button></div>
  </form>
  {error?<p role="alert" className="error-panel">{error}</p>:null}
  {loading?<p role="status">Loading matching recorded runs…</p>:searched?<>
   <p role="status">{total} matching recorded {mode==='results'?'results':'attempts'} · page {page+1}</p>
   {items.length?<div className="pnl-table-scroll"><table className="pnl-table"><caption>{mode==='results'?'Recorded valuation results':'Operational run report'} · closing valuation dates {applied.current?.from_date||'any'} → {applied.current?.to_date||'any'}</caption><thead><tr><th scope="col">Strategy / valuation period</th><th scope="col">Policy version</th>{mode==='results'?<th scope="col">Net P&amp;L / currency</th>:null}<th scope="col">Run time · London</th><th scope="col">Calculation / publication</th>{mode==='history'?<th scope="col">Failure summary</th>:null}<th scope="col">Inspect</th></tr></thead><tbody>{items.map(run=><tr key={run.attempt_id}>
    <th scope="row">{strategies.find(s=>s.id===(run.strategy_id??run.request_payload?.strategy_id))?.label??run.strategy_id??run.request_payload?.strategy_id??'Not recorded'}<br/><small>{run.request_payload?.opening_cutoff?.slice(0,10)??'—'} → {run.valuation_date??run.request_payload?.closing_cutoff?.slice(0,10)??'—'}</small></th>
    <td>{policies.find(p=>p.id===run.request_payload?.policy_id)?.label??run.request_payload?.policy_id??'Not recorded'}</td>
    {mode==='results'?<td className="pnl-amount">{run.evidence_access==='DENIED'?'Restricted — display rights required':<>{displayAmount(run.financial_summary?.netPnl??run.financial_summary?.marketPnl)} {currencies.find(c=>c.id===run.financial_summary?.reportingCurrencyId)?.label??run.financial_summary?.reportingCurrencyId??''}</>}</td>:null}
    <td>{displayTime(run.started_at)}</td><td><span className={`pnl-status pnl-status-${(run.batch_status??run.status).toLowerCase()}`}>{runStatus(run)}</span></td>
    {mode==='history'?<td>{run.failure_reason??run.error_code??'—'}</td>:null}<td><button disabled={busy||loading} onClick={()=>onOpen(run.attempt_id)}>{mode==='results'?'Open result':'View logs'}</button></td>
   </tr>)}</tbody></table></div>:<p>No matching recorded runs. No zero P&amp;L is inferred.</p>}
   <div className="pnl-pagination"><button disabled={busy||loading||page===0} onClick={()=>load(applied.current!,page-1)}>Previous</button><button disabled={busy||loading||(page+1)*25>=total} onClick={()=>load(applied.current!,page+1)}>Next</button></div>
  </>:<p className="pnl-empty">{mode==='results'?'Select a strategy and apply the filters to see its results.':'Apply filters to browse recorded attempts.'}</p>}
 </section>;
}
