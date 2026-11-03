'use client';
import {useEffect,useMemo,useRef,useState,type FormEvent,type KeyboardEvent} from 'react';
import {submitRetained,type RetainedIntent} from '@/lib/retained-mutation';
import {useRetainedNavigation} from '@/lib/use-retained-navigation';
import {UncertainRequest} from '@/components/uncertain-request';
import {PagedValuationChoice} from './paged-choice';
import {BalanceHistoryViewer} from './balance-history-chart';
import {BalanceHistoryTable} from './balance-history-table';
import {InterestDialog,InterestInputEditor} from './interest-input-editor';
import {InterestInputTable} from './interest-input-tables';
import {interestRange,interestToday,filterInterestRows} from './interest-model';
import {writeInterest} from './interest-api';
import {useInterestData} from './use-interest-data';
import type {BalanceHistoryRow,ClosingBalanceInput,DailyInterestInput,InterestContext,InterestEditor,InterestIntent,InterestOptions,InterestTab} from './interest-types';
import styles from './interest-workspace.module.css';
export {BalanceHistoryTable} from './balance-history-table';
export {InterestSource} from './interest-input-tables';
export type {BalanceHistoryRow} from './interest-types';

type InputPage<T>={items:T[]};
type HistoryPage=InputPage<BalanceHistoryRow>&{total:number;offset:number;limit:number};
const tabs:InterestTab[]=['daily','inputs','balances'];
const labels:Record<InterestTab,string>={daily:'Daily interest',inputs:'Closing balance inputs',balances:'Accrued balances'};
const validOptions=(value:unknown)=>{const item=value as InterestOptions;return !!item&&Array.isArray(item.bonds)&&Array.isArray(item.currencies)&&typeof item.canWrite==='boolean';};
const validItems=(value:unknown)=>!!value&&Array.isArray((value as InputPage<unknown>).items);
const validInputs=(value:unknown)=>validItems(value)&&(value as InputPage<DailyInterestInput|ClosingBalanceInput>).items.every(row=>row&&typeof row.input_id==='string'&&typeof row.instrument_id==='string'&&typeof row.currency_id==='string'&&typeof row.value_date==='string'&&Number.isInteger(row.revision)&&('payload' in row?!!row.payload&&typeof row.daily_earned_interest==='string':'status' in row&&(row.closing_balance===null||typeof row.closing_balance==='string')));
const validHistory=(value:unknown)=>validItems(value)&&Number.isInteger((value as HistoryPage).total)&&Number.isInteger((value as HistoryPage).offset)&&(value as HistoryPage).items.every(row=>row&&typeof row.history_id==='string'&&typeof row.instrument_name==='string'&&typeof row.basis==='string'&&(row.closing_balance===null||typeof row.closing_balance==='string'));
const emptyOptions:InterestOptions={bonds:[],currencies:[],canWrite:false};

function ResourceNotice({loading,error,onRetry}:{loading:boolean;error:string;onRetry:()=>void}){
 return loading?<p role="status">Loading records…</p>:error?<div role="alert" className={styles.error}><p>{error}</p><button type="button" onClick={onRetry}>Retry this dataset</button></div>:null;
}
function InterestNavigationGuard({pending}:{pending:{current:RetainedIntent|null}}){useRetainedNavigation(pending);return null;}

export function InterestRegister({canWrite,initialContext}:{canWrite:boolean;initialContext?:InterestContext}){
 const initial=initialContext??{strategyId:'',strategyLabel:'',from:new Date(Date.now()-14*86_400_000).toISOString().slice(0,10),to:interestToday()};
 const [context,setContext]=useState(initial),[strategy,setStrategy]=useState({id:initial.strategyId,label:initial.strategyLabel});
 const [filtersChanged,setFiltersChanged]=useState(false),[filterError,setFilterError]=useState('');
 const [tab,setTab]=useState<InterestTab>('daily'),[instrument,setInstrument]=useState(''),[offset,setOffset]=useState(0),[limit,setLimit]=useState(25);
 const [optionsRevision,setOptionsRevision]=useState(0),[dailyRevision,setDailyRevision]=useState(0),[closingRevision,setClosingRevision]=useState(0),[historyRevision,setHistoryRevision]=useState(0);
 const [editor,setEditor]=useState<InterestEditor|null>(null),[rebuild,setRebuild]=useState(false),[chartRow,setChartRow]=useState<BalanceHistoryRow|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState<Error|null>(null),[notice,setNotice]=useState(''),[needsBuild,setNeedsBuild]=useState(false);
 const pending=useRef<RetainedIntent|null>(null),sending=useRef(false);
 const noticeRef=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(notice)noticeRef.current?.focus();},[notice]);
 const locked=busy||pending.current!==null;
 const query=new URLSearchParams({strategyId:context.strategyId,fromDate:context.from,toDate:context.to}).toString();
 const balanceQuery=new URLSearchParams({strategyId:context.strategyId,fromDate:context.to,toDate:context.to}).toString();
 const optionsResource=useInterestData<InterestOptions>(context.strategyId?`interest-options?strategyId=${context.strategyId}`:null,optionsRevision,validOptions);
 const daily=useInterestData<InputPage<DailyInterestInput>>(context.strategyId?`accrual-inputs?${query}`:null,dailyRevision,validInputs);
 const closing=useInterestData<InputPage<ClosingBalanceInput>>(context.strategyId?`balance-inputs?${query}`:null,closingRevision,validInputs);
 const history=useInterestData<HistoryPage>(context.strategyId&&tab==='balances'?`balance-history?${balanceQuery}&limit=${limit}&offset=${offset}${instrument?`&instrumentId=${encodeURIComponent(instrument)}`:''}`:null,historyRevision,value=>validHistory(value)&&(value as HistoryPage).items.every(row=>row.value_date===context.to));
 const options=optionsResource.data??emptyOptions,writable=canWrite&&options.canWrite&&!optionsResource.loading&&!optionsResource.error;
 const currentContext={...context,strategyLabel:context.strategyLabel||options.strategyLabel||''};
 const dailyRows=useMemo(()=>filterInterestRows(daily.data?.items??[],instrument),[daily.data,instrument]);
 const closingRows=useMemo(()=>filterInterestRows(closing.data?.items??[],instrument),[closing.data,instrument]);
 const chartBonds=useMemo(()=>chartRow&&!options.bonds.some(bond=>bond.id===chartRow.instrument_id)?[{id:chartRow.instrument_id,label:chartRow.instrument_name,currency:chartRow.currency_code,currencyId:''},...options.bonds]:options.bonds,[chartRow,options.bonds]);

 function refresh(){setOptionsRevision(n=>n+1);setDailyRevision(n=>n+1);setClosingRevision(n=>n+1);setHistoryRevision(n=>n+1);}
 function apply(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(locked)return;
  const data=new FormData(event.currentTarget),from=String(data.get('fromDate')??''),to=String(data.get('toDate')??'');
  const invalid=interestRange(from,to);if(invalid){setFilterError(invalid);return;}
  if(!strategy.id){setFilterError('Choose a strategy before applying filters.');return;}
  const changedStrategy=context.strategyId!==strategy.id;
  setContext({strategyId:strategy.id,strategyLabel:strategy.label||(strategy.id===context.strategyId?options.strategyLabel??'':''),from,to});setOffset(0);setFiltersChanged(false);setFilterError('');setNotice('');setError(null);
  if(changedStrategy){setInstrument('');setNeedsBuild(false);}
  const url=new URL(window.location.href);for(const [key,value] of Object.entries({strategyId:strategy.id,fromDate:from,toDate:to}))url.searchParams.set(key,value);
  window.history.replaceState(window.history.state,'',url);
 }
 function openEditor(value:InterestEditor){const selected=options.bonds.find(bond=>bond.id===instrument);setError(null);setNotice('');setEditor(!value.row&&selected?{...value,prefill:{instrumentId:selected.id,currencyId:selected.currencyId,valueDate:context.to}}:value);}
 async function send(intent:InterestIntent){
  if(sending.current)return;sending.current=true;setBusy(true);setError(null);setNotice('');
  try{
   const result=await submitRetained(intent,pending,writeInterest);
   const updated=intent.path==='balance-history-refresh';
   setNotice(updated?(result.reusedBuildId?'Sources were unchanged; the retained balance build was reused.':'Accrued balances rebuilt for the selected strategy and date window. Check any unassessed or stale rows.'):`${intent.path==='accrual-inputs'?'Daily interest':intent.body.status==='WITHDRAWN'?'Closing-balance withdrawal':'Closing-balance input'} saved for ${intent.body.valueDate}. The previous revision remains in evidence.`);
   setNeedsBuild(!updated);setEditor(null);setRebuild(false);setOffset(0);refresh();
  }catch(cause){setError(cause instanceof Error?cause:new Error('The request could not be confirmed.'));}
  finally{sending.current=false;setBusy(false);}
 }
 const retry=pending.current?<UncertainRequest busy={busy} onRetry={()=>void send(JSON.parse(pending.current!.signature) as InterestIntent)}/>:null;
 function navigate(view:InterestTab){if(!locked)setTab(view);}
 function tabKey(event:KeyboardEvent<HTMLButtonElement>,view:InterestTab){
  const index=tabs.indexOf(view),next=event.key==='ArrowRight'?(index+1)%3:event.key==='ArrowLeft'?(index+2)%3:event.key==='Home'?0:event.key==='End'?2:null;
  if(next===null||locked)return;event.preventDefault();navigate(tabs[next]);document.getElementById(`interest-${tabs[next]}-tab`)?.focus();
 }
 return <section className={`pnl-workspace interest-register ${styles.workspace}`} aria-label="Interest data maintenance">
  {/* Rebind the guard to the applied URL, never while a mutation is unresolved. */}
  <InterestNavigationGuard key={query} pending={pending}/>
  <form className={styles.filters} onSubmit={apply} onChange={()=>setFiltersChanged(true)}>
   <div className={styles.filterGrid}>
    <PagedValuationChoice kind="strategies" label="Strategy" name="strategy" value={strategy.id} initialChoices={initial.strategyId?[{id:initial.strategyId,label:initial.strategyLabel||'Selected strategy'}]:[]} disabled={locked} required emptyLabel="Choose a strategy" onChange={(event,choice)=>{setStrategy({id:event.target.value,label:choice?.label??''});setFiltersChanged(true);}}/>
    <label>From date<input name="fromDate" type="date" required defaultValue={initial.from} max={interestToday()} disabled={locked}/></label>
    <label>To date<input name="toDate" type="date" required defaultValue={initial.to} max={interestToday()} disabled={locked}/></label>
   </div>
   <div className={styles.filterFooter}><p className={styles.context}>{context.strategyId?<><strong>{currentContext.strategyLabel||'Selected strategy'}</strong> · {context.from} to {context.to}{filtersChanged?' · Unapplied changes':''}</>:'Choose a strategy and the dates you want to maintain.'}</p><div className={styles.actions}><button type="submit" className={styles.primary} disabled={locked}>Apply filters</button><button type="button" disabled={locked||!context.strategyId} onClick={refresh}>Refresh data</button></div></div>
   {filterError&&<p role="alert" className={styles.fieldError}>{filterError}</p>}
  </form>
  {notice&&<div ref={noticeRef} tabIndex={-1} role="status" className={styles.notice}>{notice}</div>}
  {!editor&&!rebuild&&error&&<div role="alert" className={styles.error}>{error.message}</div>}
  {!editor&&!rebuild&&retry}
  {context.strategyId&&optionsResource.error&&<ResourceNotice loading={false} error={optionsResource.error} onRetry={()=>setOptionsRevision(n=>n+1)}/>}
  <div role="tablist" aria-label="Interest datasets" className={styles.tabs}>{tabs.map(view=><button key={view} type="button" role="tab" id={`interest-${view}-tab`} aria-controls={`interest-${view}-panel`} aria-selected={tab===view} tabIndex={tab===view?0:-1} disabled={locked} onClick={()=>navigate(view)} onKeyDown={event=>tabKey(event,view)}>{labels[view]}</button>)}</div>
  {tabs.map(view=><section key={view} role="tabpanel" id={`interest-${view}-panel`} aria-labelledby={`interest-${view}-tab`} hidden={tab!==view} tabIndex={0} className={styles.panel}>
   <header className={styles.heading}><div><h2>{labels[view]}</h2><p>{view==='daily'?'Maintain the interest earned on each value date. Correct a row to retain a new revision and its source.':view==='inputs'?'Maintain sourced end-of-day accrued balances. Use these to establish or reconcile history; they are not additional daily income.':`One row per bond and currency on the To date. Charts cover ${context.from} to ${context.to}. Older balances are not carried forward.`}</p></div>{context.strategyId&&writable&&<button type="button" className={styles.primary} disabled={locked} aria-haspopup="dialog" onClick={()=>{if(view==='balances'){setError(null);setRebuild(true);}else openEditor({kind:view==='daily'?'daily':'closing'});}}>{view==='daily'?'Add daily interest':view==='inputs'?'Add closing balance':'Rebuild balances'}</button>}</header>
   {!context.strategyId?<div className={styles.empty}><h3>Choose a strategy to begin</h3><p>Apply a date window to view and maintain its interest data.</p></div>:<>
    <div className={styles.toolbar}><label>Filter by bond<select value={instrument} disabled={locked||optionsResource.loading} onChange={event=>{setInstrument(event.target.value);setOffset(0);}}><option value="">All bonds in this strategy</option>{options.bonds.map(bond=><option key={bond.id} value={bond.id}>{bond.label} · {bond.currency}</option>)}</select></label><span className={styles.muted}>{view==='daily'&&daily.data?`${dailyRows.length} daily inputs`:view==='inputs'&&closing.data?`${closingRows.length} closing inputs`:view==='balances'&&history.data?`${history.data.total} bond/currency balances`:''}</span></div>
    {view==='balances'&&needsBuild&&<div className={styles.needsUpdate}><p><strong>Inputs changed.</strong> Rebuild balances to incorporate the saved revision. Refresh data only reloads existing records.</p></div>}
    {view==='daily'?<><ResourceNotice loading={daily.loading} error={daily.error} onRetry={()=>setDailyRevision(n=>n+1)}/>{daily.data&&<InterestInputTable kind="daily" rows={dailyRows} options={options} writable={writable} locked={locked} onEdit={openEditor}/>}</>:view==='inputs'?<><ResourceNotice loading={closing.loading} error={closing.error} onRetry={()=>setClosingRevision(n=>n+1)}/>{closing.data&&<InterestInputTable kind="closing" rows={closingRows} options={options} writable={writable} locked={locked} onEdit={openEditor}/>}</>:<>
     <ResourceNotice loading={history.loading} error={history.error} onRetry={()=>setHistoryRevision(n=>n+1)}/>
     {history.data&&(history.data.items.length?<BalanceHistoryTable rows={history.data.items} compact snapshotDate={context.to} onViewChart={setChartRow} chartDisabled={locked}/>:<div className={styles.empty}><h3>{`No maintained balances on ${context.to}`}</h3><p>Supply daily interest and any sourced opening history, then rebuild balances. Missing data remain unassessed; older dates are not substituted.</p></div>)}
     <div className={styles.pagination}><label>Rows per page<select value={limit} disabled={locked||history.loading} onChange={event=>{setLimit(Number(event.target.value));setOffset(0);}}>{[25,50,100].map(n=><option key={n} value={n}>{n}</option>)}</select></label><span aria-live="polite">{history.data?.total?`${history.data.offset+1}–${Math.min(history.data.total,history.data.offset+history.data.items.length)} of ${history.data.total}`:history.loading?'Loading…':'0 records'}</span><div className={styles.actions}><button type="button" disabled={locked||history.loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-limit))}>Previous</button><button type="button" disabled={locked||history.loading||!history.data||offset+limit>=history.data.total} onClick={()=>setOffset(offset+limit)}>Next</button></div></div>
     <details><summary>How balances are maintained</summary><p>Closing = opening + daily earned + bought accrued − sold accrued − confirmed coupon receipts. An assessed closing input can establish or reconcile the stock. Missing amounts remain unknown. Rebuilding retains evidence; it does not book cash or change a published valuation.</p></details>
    </>}
    {!optionsResource.loading&&!optionsResource.error&&!writable&&<p className={styles.muted}>Read-only for this strategy. Adding, correcting or rebuilding requires applicable valuation-run or review authority.</p>}
   </>}
  </section>)}
  {editor&&<InterestInputEditor editor={editor} context={currentContext} options={options} locked={locked} error={error} retry={retry} onSave={intent=>void send(intent)} onClose={()=>{setEditor(null);setError(null);}}/>}
  {rebuild&&<InterestDialog title="Rebuild accrued balances" description="Update the retained history from current validated inputs." locked={locked} onClose={()=>{setRebuild(false);setError(null);}}><p><strong>{currentContext.strategyLabel||'Selected strategy'}</strong> · {context.from} to {context.to}</p><p>This rebuild covers all bonds in the strategy, including any hidden by the table filter. It incorporates daily interest, trade accrual and confirmed coupon receipts. Missing source data remain unassessed.</p><p className={styles.effect}>Existing input revisions and previous build evidence remain available. No cash or valuation is booked or published.</p>{error&&<p role="alert" className={styles.error}>{error.message}</p>}{retry}<div className={styles.actions}><button type="button" className={styles.primary} disabled={locked} onClick={()=>void send({path:'balance-history-refresh',body:{strategyId:context.strategyId,fromDate:context.from,toDate:context.to}})}>{busy?'Rebuilding…':'Rebuild this date window'}</button><button type="button" disabled={locked} onClick={()=>setRebuild(false)}>Cancel</button></div></InterestDialog>}
  {chartRow&&<BalanceHistoryViewer strategyId={context.strategyId} bonds={chartBonds} initialBondId={chartRow.instrument_id} from={context.from} to={context.to} onClose={()=>setChartRow(null)}/>}
 </section>;
}
