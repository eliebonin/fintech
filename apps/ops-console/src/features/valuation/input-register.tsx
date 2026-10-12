'use client';
import {useState,type FormEvent} from 'react';
import {valuationError} from '@/lib/daily-valuation-request';
type Row={input_id:string;revision:number;value_date:string;instrument_id:string;payload:{eligibleNominal:string;sourceReference:string;eligibilityConvention:string;inputs:Record<string,string>;amounts:Record<string,string>}};
async function api<T>(path:string,init?:RequestInit){const r=await fetch(`/api/valuation/${path}`,{...init,cache:'no-store'});const data=await r.json();if(!r.ok)throw valuationError(r,data);return data as T;}
/** Source revisions precede recalculation; no edit of a financial candidate. */
export function InputRegister({strategyId,policyId,cutId,reportingCurrencyId}:{strategyId:string;policyId:string;cutId:string;reportingCurrencyId:string}){
 const [rows,setRows]=useState<Row[]>([]),[editing,setEditing]=useState<Row|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [ticket,setTicket]=useState<{key:string;body:Record<string,string>}|null>(null);
 async function load(event:FormEvent<HTMLFormElement>){event.preventDefault();const fields=new FormData(event.currentTarget);setBusy(true);setError('');
  try{const r=await api<{items:Row[]}>(`accrual-inputs?${new URLSearchParams({strategyId,fromDate:String(fields.get('fromDate')),toDate:String(fields.get('toDate'))})}`);setRows(r.items);}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function save(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=event.currentTarget;
  const next=ticket??{key:crypto.randomUUID(),body:{...(Object.fromEntries(new FormData(form)) as Record<string,string>),strategyId,policyId,cutId,reportingCurrencyId,...(editing?{supersedesInputId:editing.input_id}:{})}};
  setTicket(next);setBusy(true);setError('');
  try{const row=await api<Row>('accrual-inputs',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':next.key},body:JSON.stringify(next.body)});
   setRows(current=>[row,...current.filter(r=>r.instrument_id!==row.instrument_id||r.value_date!==row.value_date)]);setTicket(null);setEditing(null);form.reset();}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 const ready=Boolean(strategyId&&policyId&&cutId&&reportingCurrencyId);
 return <section id="valuation-input-register" className="workspace-panel"><h2>Daily input register</h2><p>Assessed bond interest: daily earned is income; the accumulated balance is a separate stock. Coupon/acquisition/disposal movements reconcile the balance, not new daily earnings. FX is selected by the chosen policy. Source corrections create immutable revisions; recalculate afterwards.</p>
  {!ready?<p>Select strategy, pricing policy and reporting currency above to manage inputs.</p>:<>
   <form onSubmit={load}><fieldset disabled={busy}><label>From date<input required type="date" name="fromDate"/></label><label>To date<input required type="date" name="toDate"/></label></fieldset><button disabled={busy}>Load assessed inputs</button></form>
   <ul>{rows.map(row=><li key={row.input_id}>{row.instrument_id} · {row.value_date} · revision {row.revision} · daily {row.payload.amounts.dailyLocal} / {row.payload.amounts.dailyBase} · balance {row.payload.amounts.balanceLocal} / {row.payload.amounts.balanceBase} <button disabled={busy||Boolean(ticket)} onClick={()=>setEditing(row)}>Correct source revision</button></li>)}</ul>
   <details open={Boolean(editing)}><summary>{editing?'Correct assessed input':'Add assessed daily input'}</summary>
    <form key={editing?.input_id??'new'} onSubmit={save}><fieldset disabled={busy||Boolean(ticket)}>
     <label>Canonical bond instrument UUID<input required name="instrumentId" defaultValue={editing?.instrument_id}/></label><label>Economic date<input required type="date" name="valueDate" defaultValue={editing?.value_date}/></label>
     {(['openingBalance','dailyEarned','closingBalance','balanceMovements'] as const).map(name=><label key={name}>{({openingBalance:'Opening accumulated balance',dailyEarned:'Daily earned interest',closingBalance:'Closing accumulated balance',balanceMovements:'Coupon / bought / sold accrued movements'})[name]} · instrument currency<input name={name} required inputMode="decimal" pattern="-?[0-9]+(\.[0-9]{1,12})?" defaultValue={editing?.payload.inputs[name]}/></label>)}
     <label>Assessed eligible nominal<input required name="eligibleNominal" inputMode="decimal" defaultValue={editing?.payload.eligibleNominal}/></label><label>Eligibility convention<input required name="eligibilityConvention" maxLength={250} defaultValue={editing?.payload.eligibilityConvention}/></label>
     <label>Source reference<input required name="sourceReference" maxLength={500} defaultValue={editing?.payload.sourceReference}/></label>
    </fieldset><button disabled={busy}>{ticket?'Retry unchanged input':'Record assessed input'}</button><button type="button" disabled={busy} onClick={()=>{setTicket(null);setEditing(null);}}>Start a different input</button></form>
   </details></>}
  {error?<p role="alert">{error}</p>:null}
 </section>;
}
