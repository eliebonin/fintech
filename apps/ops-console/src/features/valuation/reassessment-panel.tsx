'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useState,type FormEvent} from 'react';
import {displayAmount,displayTime} from './presentation';
import type {SourceHealth,Choice} from './types';
import {TechnicalReference} from './technical-reference';

const sourceLabels:Record<string,string>={MARKET_DATA:'Market prices or FX',POLICY:'Pricing policy or provider priority',CALENDAR:'Calendar or valuation-day assignment',CORPORATE_ACTION:'Corporate actions or replay decisions'};

type Target={batchId:string;strategyId:string;strategyLabel?:string;valueDate:string;publicationStatus:string;sourceHealth:SourceHealth};
type Outcome={baseBatchId:string;status:string;currency?:string;attemptId?:string|null;reason?:string;comparison?:{old:{netPnl?:string;marketPnl?:string};new:{netPnl?:string;marketPnl?:string}}};
/** Source health is operational metadata; never replace published figures locally. */
export function ReassessmentPanel({batch,canCalculate,onOpen,strategies=[]}:{batch?:{batch_id:string;sourceHealth?:SourceHealth};canCalculate:boolean;onOpen:(attempt:string)=>unknown;strategies?:Choice[]}){
 const [rows,setRows]=useState<Target[]>([]),[selected,setSelected]=useState<string[]>([]),[offset,setOffset]=useState(0),[total,setTotal]=useState(0);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[outcomes,setOutcomes]=useState<Outcome[]>([]);
 const [pending,setPending]=useState<{key:string;body:{batchIds:string[];reason:string;confirmRecalculation:true}}|null>(null);
 const health=batch?.sourceHealth;
 const targets=batch?[batch.batch_id]:selected;
 async function load(next=0){setBusy(true);setError('');try{const response=await fetch(`/api/valuation/reassessments?limit=25&offset=${next}`,{cache:'no-store'});const body=await response.json();if(!response.ok)throw new Error(body?.detail??'Reassessment list unavailable');setRows(body.items);setTotal(body.total);setOffset(next);setSelected([]);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();const reason=String(new FormData(event.currentTarget).get('reason')??'');const ticket=pending??{key:crypto.randomUUID(),body:{batchIds:targets,reason,confirmRecalculation:true as const}};setPending(ticket);setBusy(true);setError('');try{const response=await fetch('/api/valuation/reassessments/recalculate',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)});const body=await response.json();if(!response.ok)throw new Error(body?.detail??'Recalculation unavailable');setOutcomes(body.items);setPending(null);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 if(batch&&(!health||health.status==='CURRENT'))return null;
 return <section className="pnl-surface" aria-label="Valuation reassessment">
  <h3>{batch?health?.status==='UNKNOWN_LEGACY'?'Legacy source proof unavailable':'Reassessment required':'Affected valuations'}</h3>
  <p>Recorded financial results are unchanged. Recalculation creates a new staged candidate; review and publication remain separate. A warning does not by itself establish a financial error.</p>
  {health?.sourceChangeKinds?.length?<p>Changed sources: {health.sourceChangeKinds.map(kind=>(sourceLabels[kind]??kind)).join(' · ')}. Review the inputs before preparing a replacement.</p>:null}
  {health?.cashChanged?<p>Cash snapshots or uploaded coverage changed after this run. Review the cash input register and prepare a new staged calculation.</p>:null}
  {batch?<ul>{health?.changes.map((change,index)=><li key={index}>{change.reason} · <a href={`/trades/${encodeURIComponent(change.tradeId)}`}>Open affected trade</a> · effective from {change.economicFrom} · recorded {displayTime(change.recordedAt)}<TechnicalReference id={change.tradeId} label="Trade ID"/></li>)}</ul>:<>
   <button type="button" disabled={busy||Boolean(pending)} onClick={()=>load()}>Find affected valuations</button>
   {rows.length?<table className="pnl-table"><caption>Affected published and staged results</caption><thead><tr><th>Select</th><th>Strategy / valuation date</th><th>State / source health</th></tr></thead><tbody>{rows.map(row=><tr key={row.batchId}><td><input type="checkbox" aria-label={`Select ${row.valueDate} ${row.strategyLabel??'strategy'}`} disabled={busy||Boolean(pending)||!canCalculate||strategies.find(s=>s.id===row.strategyId)?.canCalculate!==true} checked={selected.includes(row.batchId)} onChange={e=>setSelected(old=>e.target.checked?[...old,row.batchId]:old.filter(id=>id!==row.batchId))}/></td><td>{row.strategyLabel??strategies.find(s=>s.id===row.strategyId)?.label??'Strategy name unavailable'} · {row.valueDate}</td><td>{row.publicationStatus} · {row.sourceHealth.status==='UNKNOWN_LEGACY'?'Legacy source proof unavailable':'Reassessment required'}</td></tr>)}</tbody></table>:null}
   <p>{total} affected results · page {offset/25+1}</p><button disabled={busy||offset===0||Boolean(pending)} onClick={()=>load(offset-25)}>Previous affected results</button><button disabled={busy||offset+25>=total||Boolean(pending)} onClick={()=>load(offset+25)}>Next affected results</button>
  </>}
  {!canCalculate?<p>Calculation permission is required to prepare replacements.</p>:<form onSubmit={submit}>
   <label>Recalculation reason<textarea name="reason" required maxLength={2000} disabled={busy||Boolean(pending)}/></label>
   <p>The new information cutoff may select newer market data too. Ad hoc attribution amendments are not automatically reapplied. Review the input evidence, amendments and old/new figures before publishing.</p>
   <label><input type="checkbox" required disabled={busy||Boolean(pending)}/> I confirm recalculation into staging, not automatic publication.</label>
   <button disabled={busy||targets.length===0}>{busy?'Recalculating…':pending?'Retry unchanged':'Recalculate affected valuations'}</button>
   {pending?<button type="button" disabled={busy} onClick={()=>setPending(null)}>Start a different request</button>:null}
  </form>}
  {error?<p role="alert">{error}</p>:null}
  {outcomes.length?<table className="pnl-table"><caption>Recalculation outcomes — not automatically published</caption><thead><tr><th>Outcome</th><th>Currency</th><th>Old net P&amp;L</th><th>New net P&amp;L</th><th>Inspect</th></tr></thead><tbody>{outcomes.map(row=><tr key={row.baseBatchId}><td>{row.status}{row.reason?` · ${row.reason}`:''}</td><td>{row.currency??'—'}</td><td>{displayAmount(row.comparison?.old.netPnl??row.comparison?.old.marketPnl)}</td><td>{displayAmount(row.comparison?.new.netPnl??row.comparison?.new.marketPnl)}</td><td>{row.attemptId?<button onClick={()=>onOpen(row.attemptId!)}>Open recalculation</button>:null}</td></tr>)}</tbody></table>:null}
 </section>;
}
