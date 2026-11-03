'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useRef,useState,type FormEvent,type KeyboardEvent} from 'react';
import {dailyValuationRequest,valuationError,ValuationHttpError} from '@/lib/daily-valuation-request';
import {ResultWorkspace} from '@/features/valuation/result-workspace';
import {displayTime} from '@/features/valuation/presentation';
import type {Batch,Detail,RecordedRequest} from '@/features/valuation/types';
import {ValuationFailureSummary} from './valuation-failure-summary';
import {MarkOverrideReview} from '@/features/valuation/mark-override-review';
import {ReviewWorkspace} from '@/features/valuation/review-workspace';
import {InputRegister} from '@/features/valuation/input-register';
import {openValuationInputs} from '@/lib/valuation-navigation';
import {RunReport,runStatus} from '@/features/valuation/run-report';
import {PublicationAction} from '@/features/valuation/publication-action';
import {ReassessmentPanel} from '@/features/valuation/reassessment-panel';
import {PagedValuationChoice} from '@/features/valuation/paged-choice';
import {ReferenceName,TechnicalReference} from '@/features/valuation/technical-reference';
import {ReportTabs,ReportPanel} from '@/features/valuation/report-tabs';
import {readReportLocation,writeReportLocation,reportViews,type ReportView} from '@/features/valuation/report-navigation';
import {RunEvidence} from '@/features/valuation/run-evidence';

type Choice={id:string;label:string;currencyId?:string|null;cutId?:string;strategyId?:string|null;canCalculate?:boolean};
type Options={strategies:Choice[];policies:Choice[];currencies:Choice[]};
const tabs=[{id:'input',label:'Input form'},{id:'results',label:'Results'},{id:'history',label:'History'}] as const;
type View=typeof tabs[number]['id'];

async function read<T>(path:string,init?:RequestInit):Promise<T>{
 const response=await fetch(`/api/valuation/${path}`,{...init,cache:'no-store'});
 const body=await response.json();
 if(!response.ok)throw valuationError(response,body);
 return body as T;
}

/** UI renders authoritative results only; it never calculates monetary values. */
export function ValuationConsole({canCalculate,canReview,actorId}:{canCalculate:boolean;canReview:boolean;actorId:string}){
 const [options,setOptions]=useState<Options>({strategies:[],policies:[],currencies:[]});
 const [detail,setDetail]=useState<Detail|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [pending,setPending]=useState<{key:string;body:Record<string,string|boolean>}|null>(null);
 const [notStarted,setNotStarted]=useState(false);
 const [strategy,setStrategy]=useState(''),[policy,setPolicy]=useState(''),[currency,setCurrency]=useState('');
 const [correction,setCorrection]=useState<{batchId:string;request:RecordedRequest}|null>(null);
 const [reportView,setReportView]=useState<ReportView>('breakdown');
 const [positionLabels,setPositionLabels]=useState<Record<string,string>>({});
 const [view,setView]=useState<View>(canCalculate?'input':'results');
 const [revision,setRevision]=useState(0);
 const inspection=useRef(0);
 const restoreLocation=useRef<()=>void>(()=>{});
 const reportSelection=useRef(reportView);reportSelection.current=reportView;
 function selectView(next:View,focus=false){setView(next);if(focus)document.getElementById(`pnl-${next}-tab`)?.focus();}
 function tabKey(event:KeyboardEvent<HTMLButtonElement>,id:View){
  const index=tabs.findIndex(tab=>tab.id===id);
  const next=event.key==='ArrowRight'?(index+1)%tabs.length:event.key==='ArrowLeft'?(index+tabs.length-1)%tabs.length:event.key==='Home'?0:event.key==='End'?tabs.length-1:null;
  if(next!==null){event.preventDefault();selectView(tabs[next].id,true);}
 }
 function refreshReports(){setRevision(current=>current+1);}
 function selectReport(next:ReportView,focus=false){
  reportSelection.current=next;setReportView(next);if(detail)writeReportLocation({attemptId:detail.attempt.attempt_id,view:next});
  if(focus)requestAnimationFrame(()=>document.getElementById(`pnl-report-${next}-tab`)?.focus());
 }
 function showDetail(next:Detail,preferred?:ReportView,mode:'push'|'replace'|'none'='push'){
  const section=preferred??(next.attempt.attempt_id===detail?.attempt.attempt_id?reportSelection.current:next.attempt.status==='FAILED'?'logs':'breakdown');
  setDetail(next);reportSelection.current=section;setReportView(section);selectView('results',true);
  if(mode!=='none')writeReportLocation({attemptId:next.attempt.attempt_id,view:section},mode);
 }
 restoreLocation.current=()=>{
  const target=readReportLocation(window.location.hash);
  if(target){if(target.attemptId===detail?.attempt.attempt_id){reportSelection.current=target.view;setReportView(target.view);selectView('results');}
   else void inspect(target.attemptId,target.view,'none');}
  else if(window.location.hash===''&&detail){inspection.current++;setDetail(null);selectView('results');}
 };
 useEffect(()=>{
  if(typeof window==='undefined')return;
  const restore=()=>restoreLocation.current();
  window.addEventListener('hashchange',restore);
  if(readReportLocation(window.location.hash))restore();
  return()=>window.removeEventListener('hashchange',restore);
 },[]);
 function remember(kind:keyof Options,choice?:Choice){if(choice)setOptions(current=>({...current,[kind]:[...current[kind].filter(item=>item.id!==choice.id),choice]}));}
 useEffect(()=>{let live=true;read<Options>('options').then(choices=>{if(live)setOptions(choices);})
  .catch(()=>{if(live)setError('Valuation choices could not be loaded. Check your access or retry.');});return()=>{live=false;inspection.current++;};},[]);
 async function inspect(id:string,section?:ReportView,mode:'push'|'replace'|'none'='push'){const generation=++inspection.current;setError('');setBusy(true);try{const next=await read<Detail>(`attempts/${id}`);if(generation===inspection.current)showDetail(next,section,mode);}catch(e){if(generation===inspection.current)setError((e as Error).message);}finally{if(generation===inspection.current)setBusy(false);}}
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const form=event.currentTarget;setError('');setNotStarted(false);
  const selectedPolicy=options.policies.find(item=>item.id===policy);
  const fields=new FormData(form);
  const ticket=pending??{key:crypto.randomUUID(),body:dailyValuationRequest(fields,{strategyId:strategy,policyId:policy,cutId:selectedPolicy?.cutId??'',reportingCurrencyId:currency,
   ...(correction?{predecessorBatchId:correction.batchId,recalculationReason:String(fields.get('recalculationReason')??'')}:{})})};
  setPending(ticket);setBusy(true);
  try{const next=await read<Detail>('attempts',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)});showDetail(next,next.attempt.status==='FAILED'?'logs':'breakdown');setPending(null);}
  catch(e){setError((e as Error).message);if(e instanceof ValuationHttpError){setNotStarted(e.notStarted);if(e.validationRejected)setPending(null);}}
  finally{setBusy(false);refreshReports();}
 }
 async function review(event:FormEvent<HTMLFormElement>,action:'explanations'|'publish'|'self-publish'){
  event.preventDefault();if(!detail?.batch)return;const comment=String(new FormData(event.currentTarget).get('comment'));
  setBusy(true);setError('');
  try{const batch=await read<Batch>(`batches/${detail.batch.batch_id}/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment,...(action==='self-publish'?{confirmSelfPublication:true}:{})})});setDetail({...detail,batch});refreshReports();}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 const batch=detail?.batch;
 const recordedRequest=batch?.summary.request??detail?.attempt.request_payload;
 const reviewStrategy=batch?.presentation?.context.strategy??detail?.attempt.display?.strategy??options.strategies.find(s=>s.id===recordedRequest?.strategy_id)?.label??'Strategy name unavailable';
 const reviewPolicy=batch?.presentation?.context.policy??detail?.attempt.display?.policy??options.policies.find(p=>p.id===recordedRequest?.policy_id)?.label??'Policy name unavailable';
 const reviewCurrency=batch?.presentation?.context.currency??options.currencies.find(c=>c.id===(recordedRequest?.reporting_currency_id??batch?.summary.reportingCurrencyId))?.label??'Currency name unavailable';
 const reviewWarnings=[...(batch?.summary.accrualCoverage?.missingCount?['Accrual not supplied—not included. Missing interest is not confirmed zero.']:[]),...(batch?.summary.cashCoverage&&batch.summary.cashCoverage.status!=='INCLUDED'?['Cash FX coverage is partial or unassessed. Missing cash is not confirmed zero.']:[]),...(batch?.summary.externalComparison==='NOT_COMPARED'?['External comparison has not been performed.']:[])];
 const selectedRunStatus=detail?runStatus({...detail.attempt,batch_status:batch?.status,publication_review_mode:batch?.publicationReviewMode,source_health_status:batch?.sourceHealth?.status,required_inputs_complete:batch?.summary.requiredInputsComplete}):'';
 return <div className="valuation-workspace pnl-workspace">
  <p className="pnl-scope-note">Economic trading P&amp;L · not full fund NAV. Recorded income/cost inputs only; historical market-only results stay labelled. {detail?<button type="button" className="pnl-text-button" onClick={()=>{selectView('results');selectReport('logs',true);}}>Scope & audit details</button>:null}</p>
  {error?<p role="alert" className="error-panel">{error}</p>:null}
  {busy?<p role="status" className="pnl-notice">Working… switching tabs does not cancel the request. Results show the selected recorded run until a new result is received.</p>:pending&&!notStarted?<p role="status" className="pnl-notice">An unchanged retry request is retained in Input form. Check History before starting a different request.</p>:null}
  <div role="tablist" aria-label="Valuation workspace" className="pnl-tabs">{tabs.map(tab=><button key={tab.id} type="button" role="tab" id={`pnl-${tab.id}-tab`} aria-controls={`pnl-${tab.id}-panel`} aria-selected={view===tab.id} tabIndex={view===tab.id?0:-1} onClick={()=>selectView(tab.id)} onKeyDown={event=>tabKey(event,tab.id)}>{tab.label}</button>)}</div>
  {/* Keep panels mounted: changing views must not discard native form values or frozen retries. */}
  <section id="pnl-input-panel" role="tabpanel" aria-labelledby="pnl-input-tab" hidden={view!=='input'} tabIndex={0} className="pnl-tab-panel">
  {canCalculate?<section className="pnl-surface pnl-calculation"><h2>Calculate and stage</h2><p className="pnl-muted">Choose the strategy, valuation period and policy. Calculation creates a review candidate, not an official publication.</p>
   <form key={correction?.batchId??'new'} onSubmit={submit} className="pnl-calculation-form"><fieldset disabled={busy||Boolean(pending)}>
    <PagedValuationChoice kind="strategies" label="Strategy" name="strategyId" required value={strategy} forCalculation initialChoices={options.strategies.filter(item=>item.canCalculate!==false)}
      onChange={(e,choice)=>{remember('strategies',choice);inspection.current++;setStrategy(e.target.value);setCurrency((choice??options.strategies.find(item=>item.id===e.target.value))?.currencyId??'');setPolicy('');setCorrection(null);}}/>
    <PagedValuationChoice kind="policies" label="Pricing policy" name="policyId" required value={policy} strategyId={strategy} initialChoices={options.policies.filter(item=>!item.strategyId||item.strategyId===strategy)}
      onChange={(e,choice)=>{remember('policies',choice);setPolicy(e.target.value);}}/>
    <PagedValuationChoice kind="currencies" label="Reporting currency" name="reportingCurrencyId" required value={currency} initialChoices={options.currencies}
      onChange={(e,choice)=>{remember('currencies',choice);setCurrency(e.target.value);}}/>
    <label>Opening valuation date<input required type="date" name="openingDate" defaultValue={correction?.request.opening_cutoff?.slice(0,10)}/></label>
    <label>Closing valuation date<input required type="date" name="closingDate" defaultValue={correction?.request.closing_cutoff?.slice(0,10)}/></label>
     {correction?<div className="pnl-recalculation-fields"><div><p>Replacement for the selected result. Correct source inputs before calculating.</p><TechnicalReference id={correction.batchId} label="Predecessor batch ID"/></div><label>Recalculation reason<textarea name="recalculationReason" required maxLength={2000}/></label></div>:null}
     <div className="pnl-calculation-options" role="group" aria-label="Calculation options">
      <div className="pnl-calculation-option">
       <label><input type="checkbox" name="requireCompleteAccruals" aria-describedby="pnl-accrual-coverage-help" defaultChecked={correction?correction.request.require_complete_accruals!==false:false}/><span>Require complete daily accrual coverage</span></label>
       <p id="pnl-accrual-coverage-help" className="pnl-muted">Supplied daily interest is always included. Leave unchecked to calculate price/FX P&amp;L with missing interest clearly flagged—not assumed zero. Check to block when any eligible bond/date lacks assessed interest.</p>
      </div>
      <div className="pnl-cash-calculation-note">
       <p><strong>Cash-balance FX P&amp;L is always assessed.</strong></p>
       <p className="pnl-muted">Uses each day's opening cash and policy-selected FX change, per account/currency. Missing cash snapshots are shown as not supplied, never zero; you may publish with this disclosed gap. Cash movements are not new income.</p>
      </div>
     </div>
    <details className="pnl-advanced"><summary>Advanced · information cutoff</summary><label>Information cutoff<input name="informationCutoff" placeholder="Blank uses submission time, retained for retries"/></label><p className="pnl-muted">Controls what evidence was known. Blank uses the current time; retries retain the original value.</p></details>
   </fieldset><button disabled={busy} type="submit">{busy?'Working…':pending?'Retry unchanged':'Calculate and stage'}</button>
   {pending?<><p>{notStarted?'This submission was not started. Check History for any earlier submission before retrying unchanged or changing the request.':'The frozen request is retained. Check run history before starting a different request; a network timeout does not cancel calculation.'}</p><button type="button" disabled={busy} onClick={()=>{setPending(null);setNotStarted(false);}}>Start a different request</button></>:null}</form></section>:<p>Read-only: inspect runs and published evidence. Calculation and review require their respective granted permissions.</p>}
  {canCalculate?<details className="pnl-surface pnl-inputs"><summary>Daily input register</summary><InputRegister key={`${strategy}:${policy}:${currency}`} strategyId={strategy} policyId={policy} cutId={options.policies.find(p=>p.id===policy)?.cutId??''} reportingCurrencyId={currency}/></details>:null}
  </section>
  <section id="pnl-results-panel" role="tabpanel" aria-labelledby="pnl-results-tab" hidden={view!=='results'} tabIndex={0} className="pnl-tab-panel">
  <div hidden={Boolean(detail)} className="pnl-report-browser"><RunReport mode="results" strategies={options.strategies} policies={options.policies} currencies={options.currencies} busy={busy} revision={revision} onOpen={id=>inspect(id)}/></div>
  {detail?<button type="button" className="pnl-back-results" disabled={busy} onClick={()=>{inspection.current++;setDetail(null);writeReportLocation(null);selectView('results',true);}}>← Back to results</button>:null}
  {detail?<button type="button" className="pnl-text-button" disabled={busy} onClick={()=>void inspect(detail.attempt.attempt_id,undefined,'replace')}>Refresh selected result and review checks</button>:null}
  {detail?<section className="pnl-current-result"><div className="pnl-result-heading"><div><p className="pnl-kicker">Selected result</p><h2>{reviewStrategy}</h2><p>{recordedRequest?.opening_cutoff?.slice(0,10)} → {recordedRequest?.closing_cutoff?.slice(0,10)}</p></div><span className={`pnl-status pnl-status-${(batch?.status??detail.attempt.status).toLowerCase()}`}>{selectedRunStatus}</span></div>
   <dl className="pnl-run-context"><div><dt>Recorded pricing policy</dt><dd><ReferenceName id={recordedRequest?.policy_id} label={reviewPolicy}/></dd></div><div><dt>Reporting currency</dt><dd><ReferenceName id={recordedRequest?.reporting_currency_id??batch?.summary.reportingCurrencyId} label={reviewCurrency}/></dd></div><div><dt>Run started · London time</dt><dd>{displayTime(detail.attempt.started_at)}</dd></div></dl>
   {batch&&batch.summary.evidenceAccess!=='DENIED'?<PublicationAction key={`publication-${batch.batch_id}`} requiredInputsComplete={batch.summary.requiredInputsComplete} sourceHealthStatus={batch.sourceHealth?.status} status={batch.status} stagedBy={batch.staged_by} actorId={actorId} canReview={canReview} busy={busy} requiresSelfReview={batch.publicationAuthority?.requiresSelfReview} canSelfPublish={batch.publicationAuthority?.canSelfPublish} unavailableReason={batch.publicationAuthority?.unavailableReason} pendingAmendments={batch.presentation?.pendingAmendments} context={{strategy:reviewStrategy,policy:reviewPolicy,currency:reviewCurrency,total:batch.summary.netPnl??batch.summary.marketPnl,period:`${recordedRequest?.opening_cutoff?.slice(0,10)??'Not recorded'} → ${recordedRequest?.closing_cutoff?.slice(0,10)??'Not recorded'}`,warnings:reviewWarnings}} onPublish={(event,selfReview)=>review(event,selfReview?'self-publish':'publish')}/>:null}
   {detail.attempt.status==='FAILED'?<ValuationFailureSummary events={detail.events}/>:null}
   {batch?<ResultWorkspace key={batch.batch_id} batch={batch} onLabels={setPositionLabels} currency={reviewCurrency} activeTab={reportView} onNavigate={selectReport} logsContent={<RunEvidence detail={detail} status={selectedRunStatus}/>} reviewContent={<>
    <MarkOverrideReview key={`marks-${batch.batch_id}`} batch={batch} active={view==='results'&&reportView==='review'}/>
    <ReassessmentPanel key={`reassess-${batch.batch_id}`} batch={batch} canCalculate={canCalculate&&options.strategies.find(s=>s.id===recordedRequest?.strategy_id)?.canCalculate===true} onOpen={id=>{void inspect(id);refreshReports();}}/>
    <ReviewWorkspace key={batch.batch_id} compact positionLabels={batch.presentation?.references??positionLabels} presentation={batch.presentation} batch={batch} canRequest={canCalculate&&options.strategies.find(s=>s.id===recordedRequest?.strategy_id)?.canCalculate!==false} canReview={canReview} actorId={actorId} onRequestsChanged={()=>{void inspect(detail.attempt.attempt_id,undefined,'replace');refreshReports();}} onOpenInputs={()=>{if(pending){setError('Resolve the retained calculation request before changing its input context.');return;}if(recordedRequest){setStrategy(recordedRequest.strategy_id);setPolicy(recordedRequest.policy_id);setCurrency(recordedRequest.reporting_currency_id);}openValuationInputs(()=>selectView('input'));}} onApproved={id=>{void inspect(id);refreshReports();}}/>
    <div className="pnl-surface pnl-decision-panel"><h3>Review & publication</h3><p className="pnl-muted">Candidate status: {batch.status}. The server rechecks access, pending requests, source revisions and independent real-operator authority before publication.</p>
    {canCalculate&&batch.summary.request&&options.strategies.find(s=>s.id===batch.summary.request?.strategy_id)?.canCalculate!==false?<button disabled={busy||Boolean(pending)} onClick={()=>{const request=batch.summary.request!;setStrategy(request.strategy_id);setPolicy(request.policy_id);setCurrency(request.reporting_currency_id);setCorrection({batchId:batch.batch_id,request});selectView('input',true);}}>Prepare corrected-input recalculation</button>:null}
    {canCalculate&&options.strategies.find(s=>s.id===recordedRequest?.strategy_id)?.canCalculate!==false&&batch.status==='STAGED'?<details><summary>Add an operations explanation</summary><form onSubmit={event=>review(event,'explanations')}><label>Ops explanation<textarea required maxLength={2000} name="comment"/></label><button disabled={busy}>Save explanation</button></form></details>:null}
    <details><summary>Explanations and decisions · {batch.reviews.length}</summary><ul>{batch.reviews.map((entry,index)=><li key={index}>{displayTime(entry.recorded_at)} · {entry.action} · {entry.comment}<ReferenceName id={entry.actor_id} label={batch.presentation?.users[entry.actor_id]} fallback="Reviewer name unavailable"/></li>)}</ul></details></div>
   </>}/>:<><ReportTabs active={reportView} onNavigate={selectReport}/>{reportViews.map(section=><ReportPanel key={section} view={section} active={reportView}>{section==='logs'?<><h3>Logs</h3><RunEvidence detail={detail} status={selectedRunStatus}/></>:<><h3>{section==='breakdown'?'Breakdown':section==='positions'?'Positions & cash':'Review'}</h3><p>No staged financial result exists for this attempt. Investigate the operational failure before starting another calculation.</p></>}</ReportPanel>)}</>}
  </section>:null}
  </section>
  <section id="pnl-history-panel" role="tabpanel" aria-labelledby="pnl-history-tab" hidden={view!=='history'} tabIndex={0} className="pnl-tab-panel">
  <RunReport mode="history" strategies={options.strategies} policies={options.policies} currencies={options.currencies} busy={busy} revision={revision} onOpen={id=>inspect(id,'logs')}/>
  <ReassessmentPanel canCalculate={canCalculate} strategies={options.strategies} onOpen={id=>{void inspect(id);refreshReports();}}/>
  </section>
 </div>;
}
