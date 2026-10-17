'use client';
import {browserFetch as fetch} from '@/lib/browser-fetch';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {parseCashCsv,type CashRow} from './cash-csv';
import {parseApiErrorResponse} from '@/lib/api-errors';
import {submitRetained,type RetainedIntent} from '@/lib/retained-mutation';
import {useRetainedNavigation} from '@/lib/use-retained-navigation';
import {UncertainRequest} from '@/components/uncertain-request';
import type {Choice} from './types';

type Account={cash_account_id:string;display_label:string|null;company_name:string;account_type:string};
type Balance={cash_balance_id:string;cash_account_id:string;currency_id:string;amount:string;revision:number;note:string|null;source_reference:string;correction_reason:string|null};
type Preview={status:string;totalReportingValue:string;inputHash:string;items:{snapshot:Balance;fxRate:string;reportingValue:string;fx:unknown}[]};
const yesterday=()=>new Date(Date.now()-86_400_000).toISOString().slice(0,10);
async function api(path:string,body?:unknown,key?:string){
 const r=await fetch(`/api/valuation/${path}`,{method:body?'POST':'GET',cache:'no-store',
  headers:body?{'Content-Type':'application/json','Idempotency-Key':key??crypto.randomUUID()}:undefined,body:body?JSON.stringify(body):undefined});
 if(!r.ok)throw await parseApiErrorResponse(r,'Cash request failed.');return r.json();
}

export function CashRegister({canWrite}:{canWrite:boolean}){
 const [options,setOptions]=useState<{strategies:Choice[];currencies:Choice[];policies:Choice[]}>({strategies:[],currencies:[],policies:[]});
 const [companies,setCompanies]=useState<{id:string;label:string}[]>([]);
 const [strategy,setStrategy]=useState(''),[valueDate,setValueDate]=useState(yesterday);
 const [accounts,setAccounts]=useState<Account[]>([]),[balances,setBalances]=useState<Balance[]>([]);
 const [revisions,setRevisions]=useState<Balance[]>([]);
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 const [correction,setCorrection]=useState<Balance|null>(null),[csv,setCsv]=useState(''),[preview,setPreview]=useState<Preview|null>(null);
 const pending=useRef<RetainedIntent|null>(null),accountPending=useRef<RetainedIntent|null>(null),epoch=useRef(0);
 useRetainedNavigation(pending,accountPending);
 const [registerState,setRegisterState]=useState<{key:string;status:'ready'|'loading'|'error'}>({key:'',status:'loading'}),[reload,setReload]=useState(0);
 const registerKey=`${strategy}:${valueDate}`;
 const ready=registerState.key===registerKey&&registerState.status==='ready';
 const writable=canWrite&&options.strategies.find(s=>s.id===strategy)?.canCalculate===true;
 useEffect(()=>{let live=true;Promise.all([api('options'),api('cash-options')]).then(([o,c])=>{if(live){setOptions(o);setCompanies(c.companies);}}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[]);
 useEffect(()=>{const current=++epoch.current;setRegisterState({key:registerKey,status:'loading'});setAccounts([]);setBalances([]);setRevisions([]);setPreview(null);setCorrection(null);setError('');setNotice('');
  if(strategy)Promise.all([api(`cash-accounts?strategyId=${strategy}`),api(`cash-balances?strategyId=${strategy}&valueDate=${valueDate}`)])
   .then(([a,b])=>{if(epoch.current===current){setAccounts(a.items);setBalances(b.items);setRevisions(b.revisions);setRegisterState({key:registerKey,status:'ready'});}}).catch(e=>{if(epoch.current===current){setError(e.message);setRegisterState({key:registerKey,status:'error'});}});
  return()=>{if(epoch.current===current)epoch.current++;};
 },[strategy,valueDate,reload]);
 async function action(work:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await work();}catch(e){setError(e instanceof Error?e.message:'Cash request failed.');}finally{setBusy(false);}}
 async function upload(rows:CashRow[]){
  await submitRetained({strategyId:strategy,rows},pending,(body,key)=>api('cash-balances',body,key));
  setNotice(`${rows.length} dated balance revision(s) saved.`);
  try{const register=await api(`cash-balances?strategyId=${strategy}&valueDate=${valueDate}`);setBalances(register.items);setRevisions(register.revisions);setPreview(null);setCorrection(null);}
  catch{setRegisterState({key:registerKey,status:'error'});throw new Error('Balance saved, but refreshed data is unavailable. Refresh the register; do not upload the saved balance again.');}
 }
 function save(e:FormEvent<HTMLFormElement>){e.preventDefault();const d=new FormData(e.currentTarget);
  void action(()=>upload([{accountId:String(d.get('accountId')),currencyId:String(d.get('currencyId')),valueDate,amount:String(d.get('amount')),
   sourceReference:String(d.get('sourceReference')),note:String(d.get('note'))||null,expectedRevision:correction?.revision??0,correctionReason:String(d.get('correctionReason'))||null}]));
 }
 return <section aria-label="Dated cash balance register"><p>Exact-date snapshots by company, account and currency. No daily unwind or carry-forward. Translated balances are not cash P&amp;L.</p>
  {error?<p role="alert" className="error-panel">{error} <button disabled={busy} onClick={()=>setReload(n=>n+1)}>Refresh register</button></p>:null}{notice?<p role="status">{notice}</p>:null}
  {pending.current?<UncertainRequest busy={busy} onRetry={()=>void action(()=>upload(JSON.parse(pending.current!.signature).rows))}/>:null}
  {accountPending.current?<UncertainRequest busy={busy} onRetry={()=>void action(async()=>{await submitRetained(JSON.parse(accountPending.current!.signature),accountPending,(body,key)=>api('cash-accounts',body,key));setNotice('Cash account saved. Refresh the register to inspect it.');setReload(n=>n+1);})}/>:null}
  <div className="strategy-form"><label>Strategy<select value={strategy} disabled={busy||!!pending.current||!!accountPending.current} onChange={e=>setStrategy(e.target.value)}><option value="">Choose a strategy</option>{options.strategies.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
   <label>Value date<input type="date" value={valueDate} max={yesterday()} disabled={busy||!!pending.current||!!accountPending.current} onChange={e=>setValueDate(e.target.value)}/></label></div>
  {strategy?<><h2>Balance register · {valueDate}</h2>{!ready?<p role="status">{registerState.key===registerKey&&registerState.status==='error'?'Balance register unavailable. No absence or zero balance can be inferred.':'Loading balance register…'}</p>:null}{ready&&balances.length?<table><thead><tr><th>Company / account</th><th>Currency</th><th>Balance</th><th>Revision</th><th>Source / note</th><th>Action</th></tr></thead><tbody>{balances.map(b=>{
   const a=accounts.find(a=>a.cash_account_id===b.cash_account_id);return <tr key={b.cash_balance_id}><td>{a?.company_name} · {a?.display_label}</td><td>{options.currencies.find(c=>c.id===b.currency_id)?.label}</td><td>{b.amount}</td><td>{b.revision}</td><td>{b.source_reference}<br/>{b.note}{b.correction_reason?<p>Correction: {b.correction_reason}</p>:null}</td><td>{writable&&ready?<button disabled={busy} onClick={()=>setCorrection(b)}>Correct balance</button>:null}</td></tr>;
  })}</tbody></table>:ready?<p>No balances uploaded for this date. This does not mean zero cash.</p>:null}
  {revisions.length?<details><summary>Snapshot revision history · {valueDate}</summary><table><thead><tr><th>Account</th><th>Currency</th><th>Revision</th><th>Balance</th><th>Note / correction reason</th></tr></thead><tbody>{revisions.map(b=><tr key={b.cash_balance_id}><td>{accounts.find(a=>a.cash_account_id===b.cash_account_id)?.display_label}</td><td>{options.currencies.find(c=>c.id===b.currency_id)?.label}</td><td>{b.revision}</td><td>{b.amount}</td><td>{b.note}<br/>{b.correction_reason}</td></tr>)}</tbody></table></details>:null}
  {writable&&ready?<><details><summary>Create a cash account</summary><form className="strategy-form" onSubmit={e=>{e.preventDefault();const d=new FormData(e.currentTarget);void action(async()=>{
   await submitRetained({strategyId:strategy,companyId:d.get('companyId'),label:d.get('label'),accountType:d.get('accountType')},accountPending,(body,key)=>api('cash-accounts',body,key));setNotice('Cash account saved.');try{setAccounts((await api(`cash-accounts?strategyId=${strategy}`)).items);}catch{setRegisterState({key:registerKey,status:'error'});throw new Error('Account saved, but refresh failed. Refresh the register instead of submitting again.');}});}}>
   <label>Maintaining company<select name="companyId" required>{companies.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label><label>Account label<input name="label" required maxLength={100}/></label>
   <label>Account kind<select name="accountType">{['CUSTODY','BANK','BROKER','EXCHANGE','MARGIN'].map(t=><option key={t}>{t}</option>)}</select></label><button disabled={busy}>Create account</button></form></details>
   <h2>{correction?'Correct dated balance':'Add dated balance'}</h2><form key={correction?.cash_balance_id??'new'} className="strategy-form" onSubmit={save}>
    <label>Company / account<select name="accountId" required defaultValue={correction?.cash_account_id}>{accounts.map(a=><option key={a.cash_account_id} value={a.cash_account_id}>{a.company_name} · {a.display_label}</option>)}</select></label>
    <label>Currency<select name="currencyId" required defaultValue={correction?.currency_id}>{options.currencies.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
    <label>Signed EoD balance<input name="amount" required inputMode="decimal" defaultValue={correction?.amount}/></label><label>Statement / source reference<input name="sourceReference" required maxLength={500} defaultValue={correction?.source_reference}/></label>
    <label>Note (optional)<textarea name="note" maxLength={2000} defaultValue={correction?.note??''}/></label>{correction?<label>Correction reason<textarea name="correctionReason" required maxLength={2000}/></label>:null}
    <button disabled={busy||!accounts.length}>{busy?'Saving…':correction?'Save correction revision':'Save balance'}</button>{correction?<button type="button" onClick={()=>setCorrection(null)}>Cancel correction</button>:null}</form>
   <details><summary>Upload balances from CSV</summary><p>Use exact account labels and currency codes. Maximum 500 rows; corrections require expectedRevision and correctionReason.</p>
    <pre>account,currency,valueDate,amount,sourceReference,note,expectedRevision,correctionReason</pre>
    <label>CSV file<input type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>{const f=e.target.files?.[0];if(f)void action(async()=>{if(f.size>1_000_000)throw new Error('CSV is limited to 1 MB.');setCsv(await f.text());});}}/></label>
    <label>CSV content<textarea value={csv} onChange={e=>setCsv(e.target.value)} rows={6}/></label><button disabled={busy||!csv} onClick={()=>void action(()=>upload(parseCashCsv(csv,accounts,options.currencies)))}>Validate and upload</button></details>
   </>:<p>Read-only for this strategy. Uploads and corrections require valuation-run access.</p>}
   <h2>Translate dated balances</h2><p>This preview is not staged, published or complete fund NAV.</p><form className="strategy-form" onSubmit={e=>{e.preventDefault();const d=new FormData(e.currentTarget);void action(async()=>{
    const policy=options.policies.find(p=>p.id===d.get('policyId'));if(!policy)throw new Error('Select a pricing policy.');
    setPreview(await api('cash-balance-preview',{strategyId:strategy,valueDate,policyId:policy.id,cutId:policy.cutId,reportingCurrencyId:d.get('reportingCurrencyId')}));});}}>
    <label>Pricing policy<select name="policyId" required>{options.policies.filter(p=>!p.strategyId||p.strategyId===strategy).map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</select></label>
    <label>Reporting currency<select name="reportingCurrencyId" required>{options.currencies.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label><button disabled={busy||!ready||!balances.length}>Preview cash value</button></form>
   {preview?<section><h3>Cash value · Preview only</h3><p>Total reporting-currency value: {preview.totalReportingValue}</p><table><thead><tr><th>Account</th><th>Balance</th><th>FX rate</th><th>Reporting value</th></tr></thead><tbody>{preview.items.map(i=><tr key={i.snapshot.cash_balance_id}><td>{accounts.find(a=>a.cash_account_id===i.snapshot.cash_account_id)?.display_label}</td><td>{i.snapshot.amount}</td><td>{i.fxRate}</td><td>{i.reportingValue}</td></tr>)}</tbody></table><details><summary>Snapshot and FX evidence</summary><pre>{JSON.stringify(preview,null,2)}</pre></details></section>:null}
  </>:null}
 </section>;
}
