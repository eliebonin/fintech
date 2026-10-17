'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useState,type FormEvent} from 'react';

type Choice={id:string;label:string};
type Period={period_id:string;coupon_key:string;accrual_start:string;accrual_end:string;payment_date:string;record_date?:string|null;ex_date?:string|null;coupon_rate:string|null;amount_per_100:string|null;rate_formula:string|null};
type Schedule={schedule_id:string;revision:number;source_reference:string;calendar_id?:string|null;day_count_convention_id?:string|null;business_day_convention?:string|null;periods:Period[]};
type Payment={payment_id:string;period_id:string;payment_date:string;amount:string;currency_id:string;source_reference:string;note:string;revision:number;status:string;cash_account_id:string|null};
type Options={strategies:Choice[];currencies:Choice[];accounts:Choice[];bonds:Choice[];permissions:Record<string,boolean>};
type Draft={path:string;body:Record<string,unknown>;key:string};
type PeriodDraft={couponKey:string;accrualStart:string;accrualEnd:string;paymentDate:string;recordDate:string;exDate:string;couponRate:string;amountPer100:string;rateFormula:string};
const blankPeriod=():PeriodDraft=>({couponKey:'',accrualStart:'',accrualEnd:'',paymentDate:'',recordDate:'',exDate:'',couponRate:'',amountPer100:'',rateFormula:''});
const endpoint='/api/lifecycle/coupons/';
async function read<T>(path:string,signal?:AbortSignal):Promise<T>{
 const response=await fetch(endpoint+path,{cache:'no-store',signal});const data=await response.json();
 if(!response.ok)throw new Error(data.detail??data.error?.message??'Coupon service unavailable.');return data;
}
export function CouponScheduleTable({periods}:{periods:Period[]}){
 return <div className="table-scroll"><table><caption>Contractual expectations — not payment confirmations</caption><thead><tr><th>Coupon</th><th>Accrual period</th><th>Scheduled payment</th><th>Rate (decimal)</th><th>Amount per 100</th><th>Formula</th></tr></thead><tbody>{periods.map(p=><tr key={p.period_id}><td>{p.coupon_key}</td><td>{p.accrual_start} → {p.accrual_end}</td><td>{p.payment_date}</td><td>{p.coupon_rate??'Not fixed / unknown'}</td><td>{p.amount_per_100??'Not fixed / unknown'}</td><td>{p.rate_formula??'—'}</td></tr>)}</tbody></table></div>;
}
function ScheduleEditor({schedule,disabled,onSave}:{schedule:Schedule|null;disabled:boolean;onSave:(fields:Record<string,unknown>)=>void}){
 const [rows,setRows]=useState<PeriodDraft[]>(schedule?.periods.map(p=>({couponKey:p.coupon_key,accrualStart:p.accrual_start,accrualEnd:p.accrual_end,paymentDate:p.payment_date,recordDate:p.record_date??'',exDate:p.ex_date??'',couponRate:p.coupon_rate??'',amountPer100:p.amount_per_100??'',rateFormula:p.rate_formula??''}))??[blankPeriod()]);
 const update=(index:number,field:keyof PeriodDraft,value:string)=>setRows(current=>current.map((row,i)=>i===index?{...row,[field]:value}:row));
 return <form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);onSave({sourceReference:data.get('source'),reason:data.get('reason'),calendarId:data.get('calendar')||null,dayCountConventionId:data.get('dayCount')||null,businessDayConvention:data.get('convention')||null,periods:rows.map(row=>Object.fromEntries(Object.entries(row).filter(([,value])=>value!==''))),confirmSchedule:true});}}><fieldset disabled={disabled}>
  <label>Source / document reference<input name="source" required maxLength={2000}/></label><label>Reason<input name="reason" required maxLength={2000}/></label>
  <details><summary>Contract conventions (optional sourced metadata)</summary><label>Calendar UUID<input name="calendar" defaultValue={schedule?.calendar_id??''}/></label><label>Day-count convention UUID<input name="dayCount" defaultValue={schedule?.day_count_convention_id??''}/></label><label>Business-day convention<select name="convention" defaultValue={schedule?.business_day_convention??''}><option value="">Not supplied</option>{['UNADJUSTED','FOLLOWING','MODIFIED_FOLLOWING','PRECEDING','MODIFIED_PRECEDING'].map(c=><option key={c}>{c}</option>)}</select></label><p>These describe the explicit source dates; saving does not recalculate dates.</p></details>
  {rows.map((row,index)=><fieldset key={index}><legend>Coupon {index+1}</legend>
   <label>Coupon identifier<input required maxLength={100} value={row.couponKey} onChange={e=>update(index,'couponKey',e.target.value)}/></label>
   {(['accrualStart','accrualEnd','paymentDate'] as const).map(field=><label key={field}>{({accrualStart:'Accrual start',accrualEnd:'Accrual end',paymentDate:'Scheduled payment'})[field]}<input type="date" required value={row[field]} onChange={e=>update(index,field,e.target.value)}/></label>)}
   <label>Coupon rate (decimal fraction, optional)<input inputMode="decimal" placeholder="0.02 means 2%" value={row.couponRate} onChange={e=>update(index,'couponRate',e.target.value)}/></label>
   <label>Amount per 100 nominal (optional)<input inputMode="decimal" value={row.amountPer100} onChange={e=>update(index,'amountPer100',e.target.value)}/></label>
   <label>Rate formula (if not fixed)<input maxLength={2000} value={row.rateFormula} onChange={e=>update(index,'rateFormula',e.target.value)}/></label>
   <details><summary>Record and ex-coupon dates</summary><label>Record date<input type="date" value={row.recordDate} onChange={e=>update(index,'recordDate',e.target.value)}/></label><label>Ex-coupon date<input type="date" value={row.exDate} onChange={e=>update(index,'exDate',e.target.value)}/></label></details>
   <button type="button" disabled={rows.length===1} onClick={()=>setRows(current=>current.filter((_,i)=>i!==index))}>Remove coupon</button>
  </fieldset>)}
  <button type="button" disabled={rows.length>=500} onClick={()=>setRows(current=>[...current,blankPeriod()])}>Add coupon period</button>
  <p>Provide a sourced rate, amount or formula. Unknown is not zero. Dates and amounts are never generated here.</p>
  <label><input type="checkbox" required/>I verified these dates and economics against the source.</label><button>Save new schedule revision</button>
 </fieldset></form>;
}
export function BondCouponConsole(){
 const [options,setOptions]=useState<Options>({strategies:[],currencies:[],accounts:[],bonds:[],permissions:{}});
 const [strategy,setStrategy]=useState(''),[instrument,setInstrument]=useState(''),[target,setTarget]=useState('');
 const [schedule,setSchedule]=useState<Schedule|null>(null),[versions,setVersions]=useState<{schedule_id:string;revision:number}[]>([]);
 const [payments,setPayments]=useState<Payment[]>([]),[total,setTotal]=useState(0),[offset,setOffset]=useState(0);
 const [from,setFrom]=useState(new Date().toISOString().slice(0,4)+'-01-01'),[to,setTo]=useState(new Date().toISOString().slice(0,10));
 const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[draft,setDraft]=useState<Draft|null>(null);
 const [editing,setEditing]=useState<Payment|null>(null),[history,setHistory]=useState<Payment[]>([]),[reload,setReload]=useState(0);
 const [scheduleRead,setScheduleRead]=useState(''),[paymentRead,setPaymentRead]=useState('');
 const scheduleKey=`${strategy}:${target}:${reload}`,paymentKey=`${strategy}:${from}:${to}:${offset}:${reload}`;
 const scheduleReady=scheduleRead===scheduleKey,paymentReady=paymentRead===paymentKey;
 useEffect(()=>{const controller=new AbortController();setOptions({strategies:[],currencies:[],accounts:[],bonds:[],permissions:{}});
  read<Options>('options'+(strategy?'?strategyId='+strategy:''),controller.signal).then(setOptions).catch(e=>{if(!controller.signal.aborted)setError(e.message);});
  return()=>controller.abort();},[strategy]);
 useEffect(()=>{setScheduleRead('');setSchedule(null);setVersions([]);if(!strategy||!target)return;const controller=new AbortController();
  read<{schedule:Schedule|null;history:typeof versions}>(`schedule?strategyId=${strategy}&instrumentId=${target}`,controller.signal)
   .then(r=>{if(!controller.signal.aborted){setSchedule(r.schedule);setVersions(r.history);setScheduleRead(scheduleKey);}}).catch(e=>{if(!controller.signal.aborted){setScheduleRead('error:'+scheduleKey);setError(e.message);}});return()=>controller.abort();},[strategy,target,reload]);
 useEffect(()=>{setPaymentRead('');setPayments([]);setTotal(0);if(!strategy)return;const controller=new AbortController();
  read<{items:Payment[];total:number}>(`payments?strategyId=${strategy}&fromDate=${from}&toDate=${to}&limit=25&offset=${offset}`,controller.signal)
   .then(r=>{if(!controller.signal.aborted){setPayments(r.items);setTotal(r.total);setPaymentRead(paymentKey);}}).catch(e=>{if(!controller.signal.aborted){setPaymentRead('error:'+paymentKey);setError(e.message);}});return()=>controller.abort();},[strategy,from,to,offset,reload]);
 const frozen=busy||draft!==null;
 async function send(ticket:Draft){setBusy(true);setError('');setMessage('');setDraft(ticket);
  try{const response=await fetch(endpoint+ticket.path,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':ticket.key},body:JSON.stringify(ticket.body)});
   const result=await response.json();if(!response.ok){if(response.status<500)setDraft(null);throw new Error(result.detail??result.error?.message??'Coupon evidence rejected.');}
   setDraft(null);setEditing(null);setReload(n=>n+1);setMessage('Evidence saved. No additional P&L, cash balance or accrued-interest changes.');
  }catch(e){setError(e instanceof Error?e.message:'Request outcome unknown. Check the report before starting another request.');}finally{setBusy(false);}}
 function submitPayment(event:FormEvent<HTMLFormElement>){event.preventDefault();const data=new FormData(event.currentTarget);
  const body:Record<string,unknown>={strategyId:strategy,periodId:editing?.period_id??data.get('period'),paymentDate:data.get('date'),amount:data.get('amount'),currencyId:data.get('currency'),sourceReference:data.get('source'),note:data.get('note'),cashAccountId:data.get('account')||null,confirmPayment:true};
  if(editing)body.supersedesPaymentId=editing.payment_id;void send({path:editing?'payments/correct':'payments',body,key:crypto.randomUUID()});}
 async function chooseVersion(id:string){setBusy(true);setError('');try{const result=await read<{schedule:Schedule}>(`schedule?strategyId=${strategy}&instrumentId=${target}&scheduleId=${id}`);setSchedule(result.schedule);}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function showHistory(id:string){setBusy(true);setError('');try{const result=await read<{items:Payment[]}>(`history?strategyId=${strategy}&paymentId=${id}`);setHistory(result.items);}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <section aria-label="Bond coupons"><p>Daily interest remains in valuation. This workspace separates expected coupons from actual payment evidence. No additional P&amp;L, automatic cash booking or accrued-balance reset.</p>
  {error&&<p role="alert">{error} <button disabled={busy} onClick={()=>{setError('');setReload(n=>n+1);}}>Refresh coupon evidence</button></p>}{message&&<p role="status">{message}</p>}
  {draft&&<aside><p>The original request is retained. Check payment history before starting a different request.</p><button disabled={busy} onClick={()=>void send(draft)}>Retry unchanged</button><button disabled={busy} onClick={()=>{setDraft(null);setReload(n=>n+1);}}>Check report / release request</button></aside>}
  <label>Strategy<select value={strategy} disabled={frozen} onChange={e=>{setStrategy(e.target.value);setTarget('');setEditing(null);setHistory([]);setOffset(0);}}><option value="">Choose a strategy</option>{options.strategies.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
  {strategy&&<><form onSubmit={e=>{e.preventDefault();setTarget(instrument);setError('');}}><label>Canonical bond<input list="coupon-bonds" required value={instrument} disabled={frozen} onChange={e=>setInstrument(e.target.value)} placeholder="Choose a traded bond or enter its canonical UUID"/></label><datalist id="coupon-bonds">{options.bonds.map(b=><option key={b.id} value={b.id}>{b.label}</option>)}</datalist><p>Suggestions include up to 100 visible bonds traded in this strategy. A late receipt can reference another visible canonical bond.</p><button disabled={frozen}>Load coupon schedule</button></form>
   <h2>Contractual schedule</h2>{target&&!scheduleReady?<p role="status">{scheduleRead==='error:'+scheduleKey?'Schedule unavailable. No absence can be inferred.':'Loading coupon schedule…'}</p>:null}{scheduleReady&&schedule?<><label>Retained version<select disabled={frozen} value={schedule.schedule_id} onChange={e=>void chooseVersion(e.target.value)}>{versions.map(v=><option key={v.schedule_id} value={v.schedule_id}>Revision {v.revision}</option>)}</select></label><p>Source: {schedule.source_reference}. Explicit sourced rows only; completeness is not inferred.</p><CouponScheduleTable periods={schedule.periods}/></>:!target||scheduleReady?<p>Load a bond to inspect its sourced schedule. No schedule does not mean no coupon.</p>:null}
   {target&&scheduleReady&&options.permissions.REFERENCE_APPROVE&&<details><summary>Maintain sourced schedule</summary><p>Creates a new immutable revision. Existing confirmations retain their original coupon period.</p><ScheduleEditor key={target+'-'+reload+'-'+schedule?.schedule_id} schedule={schedule} disabled={frozen} onSave={fields=>void send({path:'schedules',key:crypto.randomUUID(),body:{...fields,instrumentId:target,expectedRevision:versions[0]?.revision??0}})}/></details>}
   <h2>Payment confirmations</h2><p>A confirmed receipt is not a declaration that the whole coupon is settled. Daily earnings are not recognised again.</p>
   <label>From<input type="date" value={from} disabled={frozen} onChange={e=>{setFrom(e.target.value);setOffset(0);}}/></label><label>To<input type="date" value={to} disabled={frozen} onChange={e=>{setTo(e.target.value);setOffset(0);}}/></label>
   <p role="status">{!paymentReady?(paymentRead==='error:'+paymentKey?'Payment confirmations unavailable. No absence can be inferred.':'Loading payment confirmations…'):''}</p>{paymentReady&&<div className="table-scroll"><table><caption>{total} latest payment confirmations / reversals in the selected dates</caption><thead><tr><th>Actual date</th><th>Amount</th><th>Currency</th><th>Status</th><th>Source</th><th>Revision</th><th>Actions</th></tr></thead><tbody>{payments.map(p=><tr key={p.payment_id}><td>{p.payment_date}</td><td>{p.amount}</td><td>{options.currencies.find(c=>c.id===p.currency_id)?.label??p.currency_id}</td><td>{p.status}</td><td>{p.source_reference}</td><td>{p.revision}</td><td><button disabled={frozen} onClick={()=>void showHistory(p.payment_id)}>History</button>{options.permissions.TRADE_CORRECT&&<button disabled={frozen} onClick={()=>setEditing(p)}>Correct / reverse</button>}</td></tr>)}</tbody></table></div>}
   <button disabled={frozen||!paymentReady||offset===0} onClick={()=>setOffset(n=>Math.max(0,n-25))}>Previous</button><button disabled={frozen||!paymentReady||offset+25>=total} onClick={()=>setOffset(n=>n+25)}>Next</button>
   {history.length>0&&<details open><summary>Retained payment history</summary><ul>{history.map(p=><li key={p.payment_id}>Revision {p.revision} · {p.status} · {p.payment_date} · {p.amount} · {p.note||'No note'}</li>)}</ul></details>}
   {paymentReady&&((editing&&options.permissions.TRADE_CORRECT)||(!editing&&scheduleReady&&schedule&&options.permissions.LIFECYCLE_BOOK))&&<form key={editing?.payment_id??schedule?.schedule_id} onSubmit={submitPayment}><h3>{editing?'Correct retained payment':'Record actual receipt'}</h3><fieldset disabled={frozen}>
    {!editing&&<label>Coupon period<select name="period" required>{schedule?.periods.map(p=><option key={p.period_id} value={p.period_id}>{p.coupon_key} — scheduled {p.payment_date}</option>)}</select></label>}
    <label>Actual payment date<input type="date" name="date" required max={new Date().toISOString().slice(0,10)} defaultValue={editing?.payment_date}/></label><label>Signed amount<input name="amount" required inputMode="decimal" defaultValue={editing?.amount}/></label>
    <label>Currency<select name="currency" required defaultValue={editing?.currency_id??''}><option value="">Choose currency</option>{options.currencies.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
    <label>Account (optional)<select name="account" defaultValue={editing?.cash_account_id??''}><option value="">No account specified</option>{options.accounts.map(a=><option key={a.id} value={a.id}>{a.label}</option>)}</select></label>
    <label>Payment source reference<input name="source" required maxLength={2000} defaultValue={editing?.source_reference}/></label><label>{editing?'Correction reason':'Note'}<textarea name="note" required={!!editing} maxLength={2000}/></label>
    <label><input type="checkbox" required/>I confirm this sourced payment fact. No additional interest P&amp;L is created.</label><button>{editing?'Save corrected revision':'Confirm receipt'}</button></fieldset></form>}
   {editing&&<><button disabled={frozen} onClick={()=>setEditing(null)}>Cancel correction</button><form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);void send({path:'payments/reverse',key:crypto.randomUUID(),body:{strategyId:strategy,paymentId:editing.payment_id,reason:data.get('reason'),confirmPayment:true}});}}><fieldset disabled={frozen||editing.status==='REVERSED'}><label>Reversal reason<input name="reason" required maxLength={2000}/></label><label><input type="checkbox" required/>Reverse the confirmation, not the cash or daily interest.</label><button>Record reversal</button></fieldset></form></>}
  </>}
 </section>;
}
