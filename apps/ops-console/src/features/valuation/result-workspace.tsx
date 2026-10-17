'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useState} from 'react';
import {ValuationPriceEvidence} from '@/components/valuation-price-evidence';
import {InputEvidence} from './input-evidence';
import {componentLabel,displayAmount} from './presentation';
import type {Batch,Item} from './types';

function Amount({value}:{value:string|undefined}){return <span className={`pnl-amount ${value?.startsWith('-')?'pnl-negative':'pnl-positive'}`} title={value}>{displayAmount(value)}</span>;}

type ShareAdjustment={quantity_before:string;quantity_after:string;event:{effective_date:string;ratio:string;review_id:string}};
/** Exact quantities returned by the server; no browser-side action calculation. */
function ShareAdjustments({evidence}:{evidence:unknown}){
 if(!evidence||typeof evidence!=='object')return null;
 const raw=(evidence as {splitAdjustments?:unknown}).splitAdjustments;
 if(!Array.isArray(raw))return null;
 const rows=raw.filter((row):row is ShareAdjustment=>Boolean(row&&typeof row==='object'&&
  typeof row.quantity_before==='string'&&typeof row.quantity_after==='string'&&row.event&&
  typeof row.event.effective_date==='string'&&typeof row.event.ratio==='string'&&typeof row.event.review_id==='string'));
 if(!rows.length)return null;
 return <details><summary>Share quantity adjustments · {rows.length}</summary>
  <p>Reviewed basic share ratios only. Booked trades stay unchanged; no loyalty or fractional cash entitlement is inferred.</p>
  <dl>{rows.map((row,index)=><div key={`${row.event.review_id}-${index}`}><dt>{row.event.effective_date} · ratio {row.event.ratio}</dt>
   <dd>{`${row.quantity_before} → ${row.quantity_after}`}</dd><dd>Review evidence: {row.event.review_id}</dd></div>)}</dl>
 </details>;
}

/** Selection and formatting only. No allocation, invented marks or client P&L. */
export function ResultWorkspace({batch,currency,onLabels}:{batch:Batch;currency:string;onLabels?:(labels:Record<string,string>)=>void}){
 const [selected,setSelected]=useState<string|null>(null),[page,setPage]=useState(0);
 const [names,setNames]=useState<Record<string,string>>({});
 const denied=batch.summary.evidenceAccess==='DENIED';
 const rows=batch.items.slice(page*20,(page+1)*20);
 useEffect(()=>{
  if(denied)return;
  const controller=new AbortController();
  // One bounded, permission-checked label request; financial selection is not repeated.
  const ids=[...new Set(rows.map(r=>r.subject_id).filter((id):id is string=>Boolean(id)))];
  if(ids.length)void fetch(`/api/market-data/references?ids=${encodeURIComponent(ids.join(','))}`,{cache:'no-store',signal:controller.signal})
   .then(async response=>{if(!response.ok)return;const body=await response.json() as {labels:Record<string,string>};if(!controller.signal.aborted){setNames(current=>({...current,...body.labels}));onLabels?.(body.labels);}}).catch(()=>{/* Labels are optional; retained IDs remain available. */});
  return()=>controller.abort();
 },[batch.batch_id,page,denied,onLabels]);
 const item=batch.items.find(r=>r.attribution_id===selected)??rows[0];
 const label=(r:Item)=>names[r.subject_id??'']??(r.position_key?`Position ${r.subject_id??r.position_key}`:`Trade ${r.trade_id??r.attribution_id}`);
 if(denied)return <div role="status" className="pnl-notice">{batch.summary.reason??'Current dataset DISPLAY rights are required.'} The financial result is retained; review and publication are unavailable while its inputs are restricted.</div>;
 return <>
  <div className="pnl-metrics" aria-label="Batch P&L summary">
   {[['Net P&L',batch.summary.netPnl??batch.summary.marketPnl],['Gross P&L',batch.summary.grossPnl??batch.summary.marketPnl],['Market P&L',batch.summary.marketPnl]].map(([name,value])=><div key={name}><span>{name} · {currency}</span><strong><Amount value={value}/></strong></div>)}
   <div><span>Result population</span><strong>{batch.items.length} {batch.summary.resultFormat==='TRADE_V1'?(batch.items.length===1?'trade':'trades'):(batch.items.length===1?'position':'positions')}</strong></div>
  </div>
  <div className="pnl-result-grid">
   <section className="pnl-surface" aria-label="Position attribution">
    <div className="pnl-panel-heading"><h3>Position attribution</h3><span>Amounts in {currency}</span></div>
    {batch.items.length===0?<p className="pnl-empty">No relevant positions or period movements. This is a calculated, evidenced zero result.</p>:<>
     <div className="pnl-table-scroll"><table className="pnl-table"><caption>Position attribution</caption><thead><tr><th scope="col">Instrument / position</th><th scope="col">Version</th><th scope="col">Net P&L</th><th scope="col">Market P&L</th><th scope="col">Inspect</th></tr></thead>
      <tbody>{rows.map(r=><tr key={r.attribution_id} className={r.attribution_id===item?.attribution_id?'pnl-selected':''}><th scope="row">{r.subject_id?<a href={`/instruments/${encodeURIComponent(r.subject_id)}`}>{label(r)}</a>:label(r)}</th><td>v{r.version}</td><td><Amount value={r.net_pnl??r.market_pnl}/></td><td><Amount value={r.market_pnl}/></td><td><button type="button" aria-pressed={item?.attribution_id===r.attribution_id} onClick={()=>setSelected(r.attribution_id)}>Inspect position</button></td></tr>)}</tbody></table></div>
     {batch.items.length>20?<div className="pnl-pagination"><button disabled={page===0} onClick={()=>{setPage(page-1);setSelected(null);}}>Previous positions</button><span>Page {page+1} · {batch.items.length} positions</span><button disabled={(page+1)*20>=batch.items.length} onClick={()=>{setPage(page+1);setSelected(null);}}>Next positions</button></div>:null}
    </>}
   </section>
   {item?<aside className="pnl-surface pnl-inspector" aria-label="Position inspection">
    <div className="pnl-panel-heading"><div><p className="pnl-kicker">Position inspection</p><h3>{label(item)}</h3></div><span>v{item.version}</span></div>
    <p className="pnl-muted">Position-owned attribution. Original trades stay unchanged; no per-trade P&L allocation is inferred.</p>
    <table className="pnl-table pnl-components"><caption>P&L components · {currency}</caption><thead><tr><th scope="col">Component</th><th scope="col">Amount</th></tr></thead><tbody>{Object.entries(item.components).map(([name,amount])=><tr key={name}><th scope="row">{componentLabel(name)}</th><td><Amount value={amount}/></td></tr>)}</tbody></table>
    <details><summary>Prices & FX used</summary><ValuationPriceEvidence evidence={item.evidence}/><InputEvidence evidence={item.evidence}/></details>
    <ShareAdjustments evidence={item.evidence}/>
    <details><summary>Original ledger evidence · {item.lineage?.length??0} events</summary>{item.lineage?.length?<ul>{item.lineage.map(link=><li key={link.event_id}><a href={`/trades/${encodeURIComponent(link.trade_id)}`}>{link.trade_id}</a><span className="pnl-muted"> · {link.role}</span></li>)}</ul>:<p>No ledger links returned for this version.</p>}</details>
    <details><summary>Exact amounts & rounding</summary><dl>{Object.entries(item.components).map(([name,amount])=><div key={name}><dt>{componentLabel(name)}</dt><dd>{amount}</dd></div>)}</dl><pre>{JSON.stringify((item.evidence as {storageRounding?:unknown})?.storageRounding??{note:'No storage rounding evidence on this historical version.'},null,2)}</pre></details>
    <details><summary>Frozen inputs and method</summary><pre>{JSON.stringify(item.evidence,null,2)}</pre></details>
   </aside>:null}
  </div>
  <details className="pnl-bridge"><summary>Valuation bridge & scope</summary><dl>{[['Opening securities value',batch.summary.openingValue],['Closing securities value',batch.summary.closingValue],['Signed period execution value',batch.summary.executionValue],['Storage rounding adjustment',batch.summary.marketRoundingAdjustment??'0'],['External comparison',batch.summary.externalComparison]].map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl><p>Reporting currency: {currency}. Scope: {batch.summary.scope}.</p><ul>{batch.summary.limitations?.map(item=><li key={item}>{item.replaceAll('_',' ').toLowerCase()}</li>)}</ul></details>
 </>;
}
