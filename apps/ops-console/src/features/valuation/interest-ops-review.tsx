'use client';
import {useEffect,useMemo,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import {browserFetch} from '@/lib/browser-fetch';
import {parseApiErrorResponse} from '@/lib/api-errors';
import {formatTradeExactDecimal} from '@/lib/trades';
import {submitRetained,type RetainedIntent} from '@/lib/retained-mutation';
import {useRetainedNavigation} from '@/lib/use-retained-navigation';
import {UncertainRequest} from '@/components/uncertain-request';
import {PagedValuationChoice} from './paged-choice';
import {InterestDialog} from './interest-input-editor';
import {InterestPagination} from './interest-input-tables';
import {balancePage,type BalancePageSize} from './balance-chart-model';
import {exactInterestAmount,interestToday} from './interest-model';
import {useInterestData} from './use-interest-data';
import styles from './interest-workspace.module.css';

type Stage='DAILY'|'BALANCE';
type Row={instrumentId:string;instrumentName:string;currencyId:string;currency:string;amount:string|null;sourceAmount:string|null;
 decision:'ASSESSED'|'NOT_SUPPLIED';coveredDays:number;openingBalance:string|null;dailyIncrement:string|null;sourceReference:string;reason:string;notes:string[];
 benchmark:{average:string|null;coveredDays:number;requestedDays:number;startDate:string;endDate:string};
 warning:{status:string;normalizedDaily?:string;changePercent:string|null;partialBaseline:boolean;thresholdPercent:string}|null;
 reconciliation:Record<string,string>|null;details:unknown};
type View={strategyId:string;strategyLabel:string;valueDate:string;stage:Stage;sourceHash:string;rows:Row[];canWrite:boolean;
 review:{review_id:string;state:string;revision:number;gap_count:number;recorded_at:string}|null;reviewCurrent:boolean;dailyValidated:boolean;dailyReviewId:string|null;dailyGapCount?:number};
type Intent={strategyId:string;valueDate:string;stage:Stage;state:'DRAFT'|'VALIDATED';sourceHash:string;supersedesReviewId:string|null;
 rows:{instrumentId:string;currencyId:string;amount:string|null;decision:'ASSESSED'|'NOT_SUPPLIED';coveredDays:number;sourceReference:string;reason:string;reconciliation?:Record<string,string>}[]};
const valid=(value:unknown)=>!!value&&Array.isArray((value as View).rows)&&typeof (value as View).sourceHash==='string'&&(value as View).sourceHash.length===64&&(value as View).rows.every(row=>row&&typeof row.instrumentName==='string'&&typeof row.currency==='string'&&Array.isArray(row.notes)&&!!row.benchmark&&(row.amount===null||typeof row.amount==='string')&&['ASSESSED','NOT_SUPPLIED'].includes(row.decision));
const exact=(value:string|null)=>value===null?'Not supplied':formatTradeExactDecimal(value);
const diagnostic=(value:string|null|undefined)=>value==null?'No baseline':Number.isFinite(Number(value))?`≈ ${new Intl.NumberFormat('en-GB',{maximumFractionDigits:4}).format(Number(value))}`:value;
function ReviewNavigationGuard({pending}:{pending:{current:RetainedIntent|null}}){useRetainedNavigation(pending);return null;}

function ReviewEditor({row,stage,locked,onSave,onClose}:{row:Row;stage:Stage;locked:boolean;onSave:(row:Row)=>void;onClose:()=>void}){
 const [dirty,setDirty]=useState(false),[error,setError]=useState(''),[decision,setDecision]=useState(row.decision);
 function save(event:FormEvent<HTMLFormElement>){event.preventDefault();if(locked)return;const form=new FormData(event.currentTarget);
  try{
   const amount=decision==='NOT_SUPPLIED'?null:exactInterestAmount(String(form.get('amount')??'')),reason=String(form.get('reason')??'').trim(),source=String(form.get('source')??'').trim();
   if(!reason||decision==='ASSESSED'&&!source)throw new Error('A reason is required; an assessed amount also needs a source reference.');
   const coveredDays=stage==='DAILY'?Number(form.get('coveredDays')):row.coveredDays;
   if(!Number.isInteger(coveredDays)||coveredDays<1||coveredDays>31)throw new Error('Covered days must be 1–31.');
   let reconciliation=row.reconciliation;
   if(stage==='DAILY'&&reconciliation){reconciliation={...reconciliation};for(const key of ['openingBalance','closingBalance','balanceMovements'])reconciliation[key]=exactInterestAmount(String(form.get(key)??''));}
   onSave({...row,amount,decision,reason,sourceReference:source,coveredDays,reconciliation});
  }catch(cause){setError(cause instanceof Error?cause.message:'Check the input values.');}
 }
 return <InterestDialog title={stage==='DAILY'?'Assess daily accrual':'Assess closing balance'} description={`${row.instrumentName} · ${row.currency}`} locked={locked} dirty={dirty} onClose={onClose}>
  {error&&<p role="alert" className={styles.error}>{error}</p>}
  <form onSubmit={save} onChange={()=>setDirty(true)}><fieldset disabled={locked} className={styles.fields}>
   <label className={styles.full}>Assessment<select value={decision} onChange={event=>setDecision(event.target.value as Row['decision'])}><option value="ASSESSED">Supply / assess an amount</option>{row.sourceAmount===null&&<option value="NOT_SUPPLIED">Acknowledge missing input — not zero</option>}</select></label><label>{stage==='DAILY'?'Daily earned amount':'Proposed closing balance'}<input name="amount" inputMode="decimal" required={decision==='ASSESSED'} disabled={decision==='NOT_SUPPLIED'} defaultValue={row.amount??''}/><small>Original supplied / calculated value: {exact(row.sourceAmount)} {row.currency}. Zero and negative values are allowed.</small></label>
   {stage==='DAILY'&&<label>Calendar days covered<input name="coveredDays" type="number" min={1} max={31} step={1} required defaultValue={row.coveredDays}/><small>Monday normally covers three days. Adjust for holidays or another source convention. The actual amount is not divided for P&amp;L.</small></label>}
   <label className={styles.full}>Source reference<input name="source" required={decision==='ASSESSED'} maxLength={stage==='DAILY'?500:2000} defaultValue={row.sourceReference}/></label>
   <label className={styles.full}>Assessment / correction reason<textarea name="reason" required maxLength={2000} rows={3} defaultValue={row.reason}/></label>
   {stage==='DAILY'&&row.reconciliation&&<fieldset className={styles.reconciliation}><legend>Retained source reconciliation</legend><p>This source also contains a balance bridge. Update it consistently with the corrected daily amount; the service validates it.</p>{['openingBalance','closingBalance','balanceMovements'].map(key=><label key={key}>{key}<input name={key} required inputMode="decimal" defaultValue={row.reconciliation![key]}/></label>)}</fieldset>}
  </fieldset><p className={styles.effect}>This changes the review draft. Save &amp; check to retain it, then bulk validate to apply the reviewed values.</p><button className={styles.primary} type="submit" disabled={locked}>Apply to review draft</button></form>
 </InterestDialog>;
}

export function InterestOpsReview({stage,initialStrategy,initialDate}:{stage:Stage;initialStrategy:string;initialDate:string}){
 const [scope,setScope]=useState({strategy:initialStrategy,date:initialDate}),[strategy,setStrategy]=useState(initialStrategy),[revision,setRevision]=useState(0);
 const [draft,setDraft]=useState<{key:string;rows:Row[]}|null>(null),[editor,setEditor]=useState<Row|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [size,setSize]=useState<BalancePageSize>(25),[offset,setOffset]=useState(0),[confirm,setConfirm]=useState(false);
 const pending=useRef<RetainedIntent|null>(null),sending=useRef(false);
 const query=new URLSearchParams({strategyId:scope.strategy,valueDate:scope.date,stage}).toString();
 const resource=useInterestData<View>(scope.strategy?`interest-review?${query}`:null,revision,value=>valid(value)&&(value as View).strategyId===scope.strategy&&(value as View).valueDate===scope.date&&(value as View).stage===stage),view=resource.data;
 const draftKey=view?`${query}:${view.review?.review_id??'new'}:${view.sourceHash}`:'';
 const dirty=!!draft&&draft.key===draftKey,rows=dirty?draft.rows:view?.rows??[],locked=busy||pending.current!==null;
 const page=useMemo(()=>balancePage(rows,size,offset),[rows,size,offset]);
 useEffect(()=>{if(!dirty)return;
  const url=window.location.href,state=window.history.state;
  const leave=()=>window.confirm('Discard the unsaved review edits? Save & check first to retain them.');
  const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
  const click=(event:MouseEvent)=>{const link=(event.target as Element)?.closest?.('a[href]') as HTMLAnchorElement|null;if(!link||link.target==='_blank'||link.hasAttribute('download')||link.getAttribute('href')?.startsWith('#'))return;if(!leave()){event.preventDefault();event.stopPropagation();}};
  const back=(event:PopStateEvent)=>{if(!leave()){event.stopImmediatePropagation();window.history.pushState(state,'',url);}};
  window.addEventListener('beforeunload',guard);document.addEventListener('click',click,true);window.addEventListener('popstate',back,true);
  return()=>{window.removeEventListener('beforeunload',guard);document.removeEventListener('click',click,true);window.removeEventListener('popstate',back,true);};
 },[dirty]);
 function discardAllowed(){return !dirty||window.confirm('Discard the unsaved review edits? Save & check first to retain them.');}
 function apply(event:FormEvent<HTMLFormElement>){event.preventDefault();if(locked||!discardAllowed())return;const form=new FormData(event.currentTarget),day=String(form.get('valueDate')??'');
  if(!strategy||!/^\d{4}-\d{2}-\d{2}$/.test(day)){setError('Choose a strategy and value date.');return;}
  setScope({strategy,date:day});setDraft(null);setOffset(0);setError('');setNotice('');setRevision(n=>n+1);
  const url=new URL(window.location.href);url.searchParams.set('strategyId',strategy);url.searchParams.set('valueDate',day);window.history.replaceState(window.history.state,'',url);
 }
 function intent(state:'DRAFT'|'VALIDATED'):Intent{return {strategyId:scope.strategy,valueDate:scope.date,stage,state,sourceHash:view!.sourceHash,supersedesReviewId:view!.review?.review_id??null,
  rows:rows.map(row=>({instrumentId:row.instrumentId,currencyId:row.currencyId,amount:row.amount,decision:row.decision,coveredDays:row.coveredDays,sourceReference:row.sourceReference,reason:row.reason,
   ...(stage==='DAILY'&&row.reconciliation?{reconciliation:Object.fromEntries(['openingBalance','closingBalance','balanceMovements'].map(key=>[key,row.reconciliation![key]]))}:{})}))};}
 async function send(payload:Intent){
  if(sending.current)return;sending.current=true;setBusy(true);setError('');setNotice('');
  try{
   await submitRetained(payload,pending,async(body,key)=>{
    const response=await browserFetch('/api/valuation/interest-review',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:JSON.stringify(body)});
    if(!response.ok)throw await parseApiErrorResponse(response,'Review could not be saved.');
    const result=await response.json();if(!result?.review_id||result.strategy_id!==body.strategyId||result.value_date!==body.valueDate||result.stage!==body.stage||result.state!==body.state||result.row_count!==body.rows.length||result.gap_count!==body.rows.filter(row=>row.decision==='NOT_SUPPLIED').length)throw new Error('Incomplete review confirmation. Retry the original request unchanged.');return result;
   });
   setDraft(null);setConfirm(false);setNotice(payload.state==='DRAFT'?'Review draft retained. Checks have been refreshed; financial sources are unchanged.':payload.rows.some(row=>row.decision==='NOT_SUPPLIED')?'Reviewed with explicitly acknowledged gaps. Missing amounts remain unknown; no zero is recorded.':stage==='DAILY'?'All daily accruals validated. Continue to balance review.':'All closing balances validated and maintained history updated. No valuation was published.');setRevision(n=>n+1);
  }catch(cause){setError(cause instanceof Error?cause.message:'Review request failed.');}
  finally{sending.current=false;setBusy(false);}
 }
 const scopeQuery=new URLSearchParams({strategyId:scope.strategy,valueDate:scope.date}).toString();
 const dailyUrl=`/valuation/interest?${scopeQuery}`,balanceUrl=`/valuation/interest/balances?${scopeQuery}`;
 const validated=!!view?.reviewCurrent&&view.review?.state==='VALIDATED'&&!dirty;
 const canContinue=stage==='DAILY'?validated:!!view?.dailyValidated;
 const retry=pending.current?<UncertainRequest busy={busy} onRetry={()=>void send(JSON.parse(pending.current!.signature) as Intent)}/>:null;
 return <section className={`pnl-workspace interest-register ${styles.workspace}`} aria-label="Daily interest operations">
  <ReviewNavigationGuard key={query} pending={pending}/>
  <form onSubmit={apply} className={styles.filters}><div className={`${styles.filterGrid} ${styles.singleDate}`}><PagedValuationChoice kind="strategies" label="Strategy" name="strategy" value={strategy} initialChoices={[]} disabled={locked} required emptyLabel="Choose a strategy" onChange={event=>setStrategy(event.target.value)}/><label>Value date<input type="date" name="valueDate" required max={interestToday()} defaultValue={initialDate} disabled={locked}/></label></div><div className={styles.filterFooter}><p className={styles.context}>{view?.strategyLabel??'Choose a strategy'} · {scope.date}</p><div className={styles.actions}><button type="submit" disabled={locked} className={styles.primary}>Apply filters</button><button type="button" disabled={locked||!scope.strategy} onClick={()=>{if(discardAllowed()){setDraft(null);setError('');setRevision(n=>n+1);}}}>Refresh current state</button></div></div></form>
  <nav className={styles.tabs} aria-label="Interest review stages"><Link href={dailyUrl} aria-current={stage==='DAILY'?'page':undefined} onClick={event=>{if(locked)event.preventDefault();}}>1. Daily accrual review</Link>{canContinue?<Link href={balanceUrl} aria-current={stage==='BALANCE'?'page':undefined} onClick={event=>{if(locked)event.preventDefault();}}>2. Balance review</Link>:<span>2. Balance review · validate daily values first</span>}<Link href={`/valuation/interest/explorer?${new URLSearchParams({strategyId:scope.strategy,toDate:scope.date})}`} onClick={event=>{if(locked)event.preventDefault();}}>Explore balances</Link></nav>
  {notice&&<p className={styles.notice} role="status">{notice}</p>}
  {stage==='BALANCE'&&!!view?.dailyGapCount&&<p className={styles.needsUpdate}>Daily review contains {view.dailyGapCount} acknowledged missing input(s). These are unknown, not zero; closing stocks may be assessed independently.</p>}
  {error&&!confirm&&<p className={styles.error} role="alert">{error}</p>}{!confirm&&retry}
  <section className={styles.panel}><header className={styles.heading}><div><h2>{stage==='DAILY'?'Daily accrual review':'Balance review'}</h2><p>{stage==='DAILY'?'Review earned interest in each position’s local currency. Comparisons use five preceding calendar days, normalized for covered days. Changes over ±25% are informative: trades and rate changes can explain them.':'Review the opening stock, validated daily increment and proposed closing stock. Coupon and outlier notices explain changes; they do not confirm cash payment.'}</p><p className={styles.muted}>Validation retains source decisions; it does not publish P&amp;L.</p></div>{view&&<strong className={validated?styles.badge:styles.muted}>{validated?(view.review?.gap_count?'Reviewed with gaps':'Validated'):dirty?'Unsaved edits':view.review?.state==='DRAFT'&&view.reviewCurrent?'Draft · awaiting validation':'Awaiting review'}</strong>}</header>
   {!scope.strategy?<div className={styles.empty}>Choose a strategy and one value date.</div>:resource.loading?<p role="status">Loading the complete review population…</p>:resource.error?<div role="alert" className={styles.error}><p>{resource.error}</p><button type="button" disabled={locked} onClick={()=>setRevision(n=>n+1)}>Refresh current state</button>{stage==='BALANCE'&&<p><Link href={dailyUrl}>Return to daily accrual review</Link></p>}</div>:view&&<>
    <div className={styles.toolbar}><strong>{view.valueDate} · {rows.length} positions</strong><div className={styles.actions}>{view.canWrite&&<><button type="button" disabled={locked||!rows.length||!dirty} onClick={()=>void send(intent('DRAFT'))}>Save &amp; check values</button><button type="button" className={styles.primary} disabled={locked||!rows.length||validated||rows.some(row=>row.amount===null&&row.decision!=='NOT_SUPPLIED')} onClick={()=>{setError('');setConfirm(true);}}>Validate all {rows.length} {stage==='DAILY'?'daily assessments':'balance assessments'}</button></>}</div></div>
    {dirty&&<p className={styles.needsUpdate}>Unsaved edits. Save &amp; check values to retain the draft and recompute comparisons. Bulk validation applies the complete population, including other pages.</p>}
    <div className={`pnl-table-scroll ${styles.tableScroll}`}><table className="pnl-table"><caption>{stage==='DAILY'?'Local-currency daily accrual assessments':'Local-currency closing-balance assessments'}</caption><thead><tr><th>Bond / position</th><th>Currency</th>{stage==='DAILY'?<><th className="pnl-amount">Daily accrued</th><th className="pnl-amount">Per calendar day</th><th className="pnl-amount">Previous 5-day average</th></>:<><th className="pnl-amount">Before update</th><th className="pnl-amount">Daily accrual to add</th><th className="pnl-amount">New balance</th></>}<th>Checks / context</th>{view.canWrite&&<th>Action</th>}</tr></thead><tbody>{page.items.map(row=><tr key={`${row.instrumentId}:${row.currencyId}`}><td>{row.instrumentName}</td><td>{row.currency}</td>{stage==='DAILY'?<><td className="pnl-amount">{exact(row.amount)}<small className={styles.muted}> · {row.coveredDays} day{row.coveredDays===1?'':'s'}</small></td><td className="pnl-amount" title={row.warning?.normalizedDaily}>{dirty?'Save to check':diagnostic(row.warning?.normalizedDaily)}</td><td className="pnl-amount" title={row.benchmark.average??undefined}>{diagnostic(row.benchmark.average)}<small className={styles.muted}> · {row.benchmark.coveredDays}/5 days</small></td></>:<><td className="pnl-amount">{exact(row.openingBalance)}</td><td className="pnl-amount">{exact(row.dailyIncrement)}</td><td className="pnl-amount">{exact(row.amount)}</td></>}<td><span>{dirty?'Checks refresh on save':row.decision==='NOT_SUPPLIED'?'Missing input acknowledged':row.amount===null?'Assessment required':row.warning?.status==='CHECK'?`Review change (${diagnostic(row.warning.changePercent)}%)`:row.warning?.status==='CHANGED_FROM_ZERO'?'Changed from zero':row.warning?.status==='IN_LINE'?'In line':'Insufficient baseline'}</span>{row.notes.map((note,index)=><p className={styles.muted} key={index}>{note}</p>)}{row.warning?.partialBaseline&&stage==='DAILY'&&<p className={styles.muted}>Incomplete five-day benchmark; missing days are not zero.</p>}<details><summary>Source &amp; review evidence</summary><p>{row.sourceReference||'No source supplied'}</p><p>{row.reason}</p><pre>{JSON.stringify(row,null,2)}</pre></details></td>{view.canWrite&&<td><button type="button" disabled={locked} aria-haspopup="dialog" aria-label={`Assess ${row.instrumentName}`} onClick={()=>setEditor(row)}>Assess / edit</button></td>}</tr>)}</tbody></table></div>
    <InterestPagination size={size} onSize={setSize} offset={page.start} count={page.items.length} total={page.total} onOffset={setOffset} disabled={locked}/>
    {validated&&stage==='DAILY'&&<p><Link href={balanceUrl}>Continue to balance review →</Link></p>}
    {view.review&&<details><summary>Retained review receipt · revision {view.review.revision}</summary><pre>{JSON.stringify(view.review,null,2)}</pre></details>}
   </>}
  </section>
  {editor&&<ReviewEditor row={editor} stage={stage} locked={locked} onClose={()=>setEditor(null)} onSave={row=>{setDraft({key:draftKey,rows:rows.map(old=>old.instrumentId===row.instrumentId&&old.currencyId===row.currencyId?row:old)});setEditor(null);}}/>}
  {confirm&&<InterestDialog title={stage==='DAILY'?'Validate all daily accruals':'Validate all closing balances'} description={`${view?.strategyLabel??'Selected strategy'} · ${scope.date}`} locked={locked} onClose={()=>setConfirm(false)}><p>This reviews all {rows.length} positions, including rows on other pages: {rows.filter(row=>row.decision!=='NOT_SUPPLIED').length} assessed amounts and {rows.filter(row=>row.decision==='NOT_SUPPLIED').length} explicitly acknowledged gaps. Missing amounts remain unknown and are not zero. Outlier checks are informative; confirm that you have assessed them.</p><p>{stage==='DAILY'?'Reviewed source corrections will be recorded and balance review becomes available.':'Reviewed closing stocks will be recorded and the maintained daily balance history updated.'} No cash is booked and no P&amp;L is published.</p>{error&&<p role="alert" className={styles.error}>{error}</p>}{retry}<button type="button" className={styles.primary} disabled={locked} onClick={()=>void send(intent('VALIDATED'))}>{busy?'Validating…':'Confirm bulk validation'}</button></InterestDialog>}
 </section>;
}
