'use client';
import {useEffect,useState,type FormEvent} from 'react';
import {dailyValuationRequest,valuationError,ValuationHttpError} from '@/lib/daily-valuation-request';
import {ValuationPriceEvidence} from './valuation-price-evidence';
import {ValuationFailureSummary} from './valuation-failure-summary';
import {ReviewWorkspace} from '@/features/valuation/review-workspace';
import {InputRegister} from '@/features/valuation/input-register';

type Attempt={attempt_id:string;request_key:string;status:string;started_at:string;error_code:string|null;correlation_id:string};
type Choice={id:string;label:string;currencyId?:string|null;cutId?:string;strategyId?:string|null};
type Options={strategies:Choice[];policies:Choice[];currencies:Choice[]};
type Batch={batch_id:string;status:string;staged_by:string;summary:{scope:string;marketPnl:string;openingValue:string;closingValue:string;executionValue:string;
 request?:Record<string,string>;grossPnl?:string;netPnl?:string;reportingCurrencyId:string;externalComparison:string;limitations:string[];resultFormat?:'POSITION_V2'|'TRADE_V1';evidenceAccess?:'DENIED';reason?:string};items:{attribution_id:string;trade_id:string|null;position_key?:string|null;subject_id?:string|null;version:number;market_pnl:string;gross_pnl?:string;net_pnl?:string;components:Record<string,string>;evidence:unknown;lineage?:{trade_id:string;event_id:string;role:string}[]}[];
 reviews:{actor_id:string;action:string;comment:string;recorded_at:string}[]};
type Detail={attempt:Attempt;events:{event_id:string;event_code:string;stage:string;recorded_at:string;details:unknown}[];batch:Batch|null};

async function read<T>(path:string,init?:RequestInit):Promise<T>{
 const response=await fetch(`/api/valuation/${path}`,{...init,cache:'no-store'});
 const body=await response.json();
 if(!response.ok)throw valuationError(response,body);
 return body as T;
}

/** UI renders authoritative results only; it never calculates monetary values. */
export function ValuationConsole({canCalculate,canReview,actorId}:{canCalculate:boolean;canReview:boolean;actorId:string}){
 const [options,setOptions]=useState<Options>({strategies:[],policies:[],currencies:[]});
 const [attempts,setAttempts]=useState<Attempt[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(0);
 const [detail,setDetail]=useState<Detail|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [pending,setPending]=useState<{key:string;body:Record<string,string>}|null>(null);
 const [strategy,setStrategy]=useState(''),[policy,setPolicy]=useState(''),[currency,setCurrency]=useState('');
 const [correction,setCorrection]=useState<{batchId:string;request:Record<string,string>}|null>(null);
 async function history(offset=page){const result=await read<{items:Attempt[];total:number}>(`attempts?limit=25&offset=${offset*25}`);setAttempts(result.items);setTotal(result.total);}
 useEffect(()=>{let live=true;Promise.all([read<Options>('options'),read<{items:Attempt[];total:number}>('attempts?limit=25&offset=0')])
  .then(([choices,list])=>{if(live){setOptions(choices);setAttempts(list.items);setTotal(list.total);}})
  .catch(()=>{if(live)setError('Valuation history could not be loaded. Check your access or retry.');});return()=>{live=false;};},[]);
 async function inspect(id:string){setError('');setBusy(true);try{setDetail(await read<Detail>(`attempts/${id}`));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const form=event.currentTarget;setError('');
  const selectedPolicy=options.policies.find(item=>item.id===policy);
  const fields=new FormData(form);
  const ticket=pending??{key:crypto.randomUUID(),body:dailyValuationRequest(fields,{strategyId:strategy,policyId:policy,cutId:selectedPolicy?.cutId??'',reportingCurrencyId:currency,
   ...(correction?{predecessorBatchId:correction.batchId,recalculationReason:String(fields.get('recalculationReason')??'')}:{})})};
  setPending(ticket);setBusy(true);
  try{setDetail(await read<Detail>('attempts',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)}));setPending(null);}
  catch(e){setError((e as Error).message);if(e instanceof ValuationHttpError&&e.validationRejected)setPending(null);}
  finally{setBusy(false);try{await history();}catch{setError(current=>current||'Refresh run history to check the calculation outcome.');}}
 }
 async function review(event:FormEvent<HTMLFormElement>,action:'explanations'|'publish'){
  event.preventDefault();if(!detail?.batch)return;const comment=String(new FormData(event.currentTarget).get('comment'));
  setBusy(true);setError('');
  try{const batch=await read<Batch>(`batches/${detail.batch.batch_id}/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment})});setDetail({...detail,batch});await history();}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 const batch=detail?.batch;
 return <div className="valuation-workspace">
  <p>This is economic trading P&amp;L from supported positions and recorded income/cost inputs, not full fund NAV. Historical market-only results remain labelled. Corporate-action replay and stock cash balances are not enabled. Missing inputs block calculation; provider comparison is NOT_COMPARED unless independently performed.</p>
  {error?<p role="alert" className="error-panel">{error}</p>:null}
  {canCalculate?<section className="workspace-panel"><h2>Calculate and stage</h2><p>Supported equities/ETFs, governed fund NAV and bonds with assessed daily accrual. Cross-currency reporting requires independently selected FX; prices require native RAW or verified as-traded normalization. Unsupported product economics remain blocked. Positions use valuation-effective dates under the UTC business-date convention.</p>
   <form key={correction?.batchId??'new'} onSubmit={submit} className="strategy-form"><fieldset disabled={busy||Boolean(pending)}>
    <label>Strategy<select required value={strategy} onChange={e=>{setStrategy(e.target.value);setCurrency(options.strategies.find(item=>item.id===e.target.value)?.currencyId??'');setPolicy('');setDetail(null);setCorrection(null);}}><option value="">Select strategy</option>{options.strategies.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    <label>Pricing policy<select required value={policy} onChange={e=>setPolicy(e.target.value)}><option value="">Select policy</option>{options.policies.filter(item=>!item.strategyId||item.strategyId===strategy).map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    <label>Reporting currency<select required value={currency} onChange={e=>setCurrency(e.target.value)}><option value="">Select currency</option>{options.currencies.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    <label>Opening valuation date<input required type="date" name="openingDate" defaultValue={correction?.request.opening_cutoff?.slice(0,10)}/></label>
    <label>Closing valuation date<input required type="date" name="closingDate" defaultValue={correction?.request.closing_cutoff?.slice(0,10)}/></label>
    {correction?<><p>Replacement for batch {correction.batchId}. Correct source inputs before calculating.</p><label>Recalculation reason<textarea name="recalculationReason" required maxLength={2000}/></label></>:null}
    <label>Information cutoff<input name="informationCutoff" placeholder="Blank uses submission time, retained for retries"/></label>
   </fieldset><button disabled={busy} type="submit">{busy?'Working…':pending?'Retry unchanged':'Calculate and stage'}</button>
   {pending?<><p>The frozen request is retained. Check run history before starting a different request; a network timeout does not cancel calculation.</p><button type="button" disabled={busy} onClick={()=>setPending(null)}>Start a different request</button></>:null}</form></section>:<p>Read-only: inspect runs and published evidence. Calculation and review require their respective granted permissions.</p>}
  {canCalculate?<InputRegister key={`${strategy}:${policy}:${currency}`} strategyId={strategy} policyId={policy} cutId={options.policies.find(p=>p.id===policy)?.cutId??''} reportingCurrencyId={currency}/>:null}
  <section className="workspace-panel"><h2>Run history</h2><button disabled={busy} onClick={()=>history().catch(()=>setError('Run history could not be refreshed.'))}>Refresh history</button>
   {attempts.length?<div className="workspace-table-scroll"><table><thead><tr><th>Started UTC</th><th>Status</th><th>Inspect</th></tr></thead><tbody>{attempts.map(attempt=><tr key={attempt.attempt_id}><td>{attempt.started_at}</td><td>{attempt.status}{attempt.error_code?` · ${attempt.error_code}`:''}</td><td><button disabled={busy} onClick={()=>inspect(attempt.attempt_id)}>Open run</button></td></tr>)}</tbody></table></div>:<p>No runs loaded. No zero P&amp;L is inferred.</p>}
   <p>{total} recorded attempts · page {page+1}</p><button disabled={busy||page===0} onClick={()=>{setPage(page-1);history(page-1).catch(()=>setError('Page could not be loaded.'));}}>Previous</button> <button disabled={busy||(page+1)*25>=total} onClick={()=>{setPage(page+1);history(page+1).catch(()=>setError('Page could not be loaded.'));}}>Next</button>
  </section>
  {detail?<section className="workspace-panel"><h2>Run evidence</h2><p>{detail.attempt.status} · correlation {detail.attempt.correlation_id}</p>
   {detail.attempt.status==='FAILED'?<ValuationFailureSummary events={detail.events}/>:null}
   <h3>Operational log</h3><ul>{detail.events.map(event=><li key={event.event_id}>{event.recorded_at} · {event.stage} · {event.event_code}<details><summary>Technical details (JSON)</summary><pre>{JSON.stringify(event.details,null,2)}</pre></details></li>)}</ul>
   {batch?batch.summary.evidenceAccess==='DENIED'?<p role="status">{batch.summary.reason??'Current dataset display rights are required to inspect this result.'} The financial result is retained; review and publication are unavailable while its inputs are restricted.</p>:<><h3>Attribution review · {batch.status}</h3><dl><dt>Market P&amp;L</dt><dd>{batch.summary.marketPnl}</dd><dt>Opening securities value</dt><dd>{batch.summary.openingValue}</dd><dt>Closing securities value</dt><dd>{batch.summary.closingValue}</dd><dt>Signed period execution value</dt><dd>{batch.summary.executionValue}</dd><dt>External comparison</dt><dd>{batch.summary.externalComparison}</dd></dl>
    <p>Reporting currency: {options.currencies.find(item=>item.id===batch.summary.reportingCurrencyId)?.label??batch.summary.reportingCurrencyId}</p>
    {batch.summary.resultFormat==='POSITION_V2'?<p>Position-based attribution. Original executions remain linked as evidence; this is not realised/unrealised cost-basis accounting.</p>:null}
    {batch.summary.resultFormat==='POSITION_V2'&&batch.items.length===0?<p>No relevant positions or period movements. This is a calculated, evidenced zero result.</p>:null}
    {batch.items.map(item=><details key={item.attribution_id}><summary>{item.position_key?`Position ${item.subject_id}`:`Trade ${item.trade_id}`} · version {item.version} · market P&amp;L {item.market_pnl}</summary><pre>{JSON.stringify(item.components,null,2)}</pre>
     {item.lineage?.length?<><h4>Original ledger evidence</h4><ul>{item.lineage.map(link=><li key={link.event_id}><a href={`/trades/${encodeURIComponent(link.trade_id)}`}>{link.trade_id}</a> · {link.role}</li>)}</ul></>:null}
     <ValuationPriceEvidence evidence={item.evidence}/><details><summary>Frozen inputs and method</summary><pre>{JSON.stringify(item.evidence,null,2)}</pre></details></details>)}
    <ReviewWorkspace key={batch.batch_id} batch={batch} canRequest={canCalculate} canReview={canReview} actorId={actorId} onApproved={id=>{void inspect(id);void history();}}/>
    <h3>Explanations and decisions</h3><ul>{batch.reviews.map((entry,index)=><li key={index}>{entry.recorded_at} · {entry.action} · {entry.comment}</li>)}</ul>
    {canCalculate&&batch.summary.request?<button disabled={busy||Boolean(pending)} onClick={()=>{const request=batch.summary.request!;setStrategy(request.strategy_id);setPolicy(request.policy_id);setCurrency(request.reporting_currency_id);setCorrection({batchId:batch.batch_id,request});}}>Prepare corrected-input recalculation</button>:null}
    {canCalculate&&batch.status==='STAGED'?<form onSubmit={event=>review(event,'explanations')}><label>Ops explanation<textarea required maxLength={2000} name="comment"/></label><button disabled={busy}>Save explanation</button></form>:null}
    {canReview&&batch.status==='STAGED'?(batch.staged_by===actorId?<p>An independent reviewer must review and publish this batch. You staged it.</p>:<form onSubmit={event=>review(event,'publish')}><label>Review decision<textarea required maxLength={2000} name="comment"/></label><button disabled={busy}>Publish reviewed P&amp;L</button></form>):null}
   </>:<p>No staged financial result exists for this attempt. Investigate the operational failure before starting another calculation.</p>}
  </section>:null}
 </div>;
}
