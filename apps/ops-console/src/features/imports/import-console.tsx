'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {browserFetch} from '@/lib/browser-fetch';
import {decodeFile,importStatus,type ImportJob} from './import-model';
import {ImportReview} from './import-review';
import {ImportHistory} from './import-history';
import styles from './imports.module.css';

type Options={strategies:{id:string;label:string}[];maxRows:number;maxBytes:number;products:string[]};
type Pending={path:string;body:Record<string,unknown>;key:string};
async function readFile(file:File):Promise<string>{return new Promise((resolve,reject)=>{
 const reader=new FileReader();reader.onerror=()=>reject(new Error('File could not be read.'));
 reader.onload=()=>{try{resolve(decodeFile(String(reader.result)));}catch(error){reject(error);}};reader.readAsDataURL(file);
});}
async function request<T>(path:string,init?:RequestInit):Promise<T>{
 const response=await browserFetch(`/api/trade-imports/${path}`,{cache:'no-store',...init});
 const result=await response.json();
 if(!response.ok)throw Object.assign(new Error(result.error?.message??result.detail??'Import request failed.'),{status:response.status});
 return result as T;
}
export function ImportConsole({tenantId,canWrite}:{tenantId:string;canWrite:boolean}){
 const [tab,setTab]=useState<'new'|'history'>('new');const [options,setOptions]=useState<Options|null>(null);
 const [strategy,setStrategy]=useState('');const [source,setSource]=useState('');const [file,setFile]=useState<File|null>(null);
 const [jobs,setJobs]=useState<ImportJob[]>([]);const [historyOffset,setHistoryOffset]=useState(0);const [historyTotal,setHistoryTotal]=useState(0);
 const [job,setJob]=useState<ImportJob|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [notice,setNotice]=useState('');const [uncertain,setUncertain]=useState(false);const pending=useRef<Pending|null>(null);
 const [historyLoaded,setHistoryLoaded]=useState(false);const reviewHeading=useRef<HTMLHeadingElement>(null);
 const loadHistory=useCallback(async()=>{const data=await request<{items:ImportJob[];total:number}>(`history?offset=${historyOffset}`);setJobs(data.items);setHistoryTotal(data.total);setHistoryLoaded(true);},[historyOffset]);
 useEffect(()=>{let active=true;
  if(canWrite)request<Options>('options').then(data=>{if(active)setOptions(data);}).catch(e=>{if(active)setError(e.message);});
  return()=>{active=false;};
 },[canWrite]);
 useEffect(()=>{loadHistory().catch(e=>setError(e.message));},[loadHistory]);
 // Announce a newly opened review or validation/booking outcome, not every row-page read.
 useEffect(()=>{if(tab==='new'&&job)reviewHeading.current?.focus();},[tab,job?.jobId,job?.status]);
 async function open(id:string,offset=0){setError('');setBusy(true);try{setJob(await request<ImportJob>(`${id}?offset=${offset}`));setTab('new');}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function execute(intent:Pending){
  pending.current=intent;setBusy(true);setError('');setNotice('');setUncertain(false);
  try{
   const result=await request<ImportJob>(intent.path,{method:'POST',headers:{'Content-Type':'application/json','X-Expected-Tenant-Id':tenantId,'Idempotency-Key':intent.key},body:JSON.stringify(intent.body)});
   setJob(result);pending.current=null;setNotice(importStatus(result));
   loadHistory().catch(()=>setNotice('The command completed. History could not refresh; reload history to inspect it.'));
  }catch(e){
   const failure=e as Error&{status?:number};setError(failure.message);
   // 5xx/timeouts may follow a committed transaction. Keep the exact payload/key.
   if(!failure.status||failure.status>=500){setUncertain(true);}else{pending.current=null;}
  }finally{setBusy(false);}
 }
 async function upload(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();if(!file||!strategy)return;
  if(file.size>524288){setError('Select a file of at most 512 KiB.');return;}
  setBusy(true);setError('');
  try{await execute({path:'create',body:{strategyId:strategy,source,filename:file.name,contentBase64:await readFile(file)},key:crypto.randomUUID()});}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 const disabled=busy||uncertain;
 const step=job?3:strategy?2:1;
 const strategyLabel=options?.strategies.find(item=>item.id===(job?.strategyId??strategy))?.label??'Selected strategy';
 function startNew(){if(disabled)return;setJob(null);setFile(null);setError('');setNotice('');setTab('new');}
 return <main className={`mvp-page ${styles.page}`}>
  <header className={styles.header}><div><p className="eyebrow">TENANT DATA INTAKE</p><h1>Trade imports</h1><p>Prepare your file, check every row, then book the batch with confidence.</p></div><div className={styles.actions}>
   {job&&canWrite?<button className={styles.secondary} type="button" disabled={disabled} onClick={startNew}>New import</button>:null}<Link href="/trades">Trade history</Link></div></header>
<details className={styles.help}><summary>How to use this page</summary><ol><li>Download the template for your permitted strategy and fill in its trade table.</li><li>Keep financial values and identifiers as text. Use ISO dates and timestamps with a timezone.</li><li>Use the same file source and stable trade IDs for repeat deliveries.</li><li>Validate all rows, inspect proposed trades and custom properties, then explicitly confirm booking.</li></ol><p>Already-booked IDs are recognised, not booked twice. Correct an unbooked file and upload a revised copy. Changes to booked trades use the normal cancel/replace workflow. No automatic countercash or valuation publication occurs.</p></details>
  <nav className={styles.tabs} aria-label="Import views"><button type="button" aria-pressed={tab==='new'} onClick={()=>setTab('new')}>Upload & review</button><button type="button" aria-pressed={tab==='history'} onClick={()=>setTab('history')}>Import history</button></nav>
  {error?<div className="error-panel" role="alert"><h2>Import needs attention</h2><p>{error}</p></div>:null}
  {notice&&(tab==='history'||!job||notice!==importStatus(job))?<p className={styles.live} role="status">{notice}</p>:null}
  {uncertain?<aside className={`${styles.card} ${styles.error}`}><h2>Outcome not yet confirmed</h2><p>Do not start a different booking. Retry the exact retained request, or inspect its job/history. A timeout does not mean nothing was booked.</p><div className={styles.actions}><button disabled={busy} onClick={()=>pending.current&&execute(pending.current)}>Retry unchanged request</button>{job?<button className={styles.secondary} disabled={busy} onClick={()=>open(job.jobId)}>Check retained job</button>:null}</div></aside>:null}
  {tab==='history'?<ImportHistory jobs={jobs} total={historyTotal} offset={historyOffset} busy={busy} disabled={disabled} loaded={historyLoaded}
   onRefresh={()=>loadHistory().catch(e=>setError(e.message))} onOpen={id=>open(id)} onPage={setHistoryOffset}/>:
   <>
    {canWrite?<ol className={styles.steps} aria-label="Import progress">{[['Prepare','Choose strategy & template'],['Upload','Select file & source'],['Review & book','Validate, inspect, confirm']].map(([label,description],index)=><li key={label} aria-current={step===index+1?'step':undefined}><span className={styles.stepNumber}>{index+1}</span><span><strong>{label}</strong><small>{description}</small></span></li>)}</ol>:null}
    {job?<ImportReview job={job} strategyLabel={strategyLabel} canWrite={canWrite} disabled={disabled} busy={busy} headingRef={reviewHeading}
     onValidate={()=>execute({path:`${job.jobId}/validate`,body:{},key:crypto.randomUUID()})}
     onConfirm={()=>execute({path:`${job.jobId}/confirm`,body:{reviewHash:job.reviewHash},key:`confirm-${job.jobId}-${job.reviewHash}`})}
     onPage={offset=>open(job.jobId,offset)}/>:
     canWrite?<form onSubmit={upload}><div className={styles.setup}>
      <section className={styles.card} aria-labelledby="prepare-heading"><span className={styles.kicker}>Step 1</span><h2 id="prepare-heading">Prepare your template</h2><p className={styles.intro}>Choose the strategy you are booking into. Its Excel template includes your tenant’s optional fields and governed dropdowns.</p>
       <div className={styles.field}><label htmlFor="import-strategy">Strategy</label><select id="import-strategy" required value={strategy} disabled={disabled||!options} onChange={e=>setStrategy(e.target.value)}><option value="">{options?'Select a permitted strategy':'Loading permitted strategies…'}</option>{options?.strategies.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select>
        {options&&!options.strategies.length?<p className={styles.hint}>No strategies are available for booking. Ask your tenant administrator to review your strategy permissions.</p>:null}</div>
       <div className={styles.download}>{strategy?<a href={`/api/trade-imports/template?strategyId=${encodeURIComponent(strategy)}`}><strong>Download tenant-specific Excel template</strong></a>:<strong>Select a strategy to unlock its template</strong>}<p className={styles.hint}>Fill in the Trades sheet. Use listing UUIDs from the catalogue, exact text values and ISO dates. Dropdowns help entry; the server checks everything again.</p></div>
       <div className={styles.limits}><span>Equities / ETFs / funds</span><span>Up to 500 trades</span><span>512 KiB per file</span></div><Link href="/instruments">Browse the instrument catalogue</Link>
      </section>
      <section className={`${styles.card} ${!strategy?styles.disabled:''}`} aria-labelledby="upload-heading"><span className={styles.kicker}>Step 2</span><h2 id="upload-heading">Upload your trade file</h2><p className={styles.intro}>Uploading retains your file for review. It does not book any trades.</p>
       <div className={styles.field}><label htmlFor="import-source">File source</label><input id="import-source" aria-describedby="import-source-help" required value={source} disabled={disabled||!strategy} maxLength={100} pattern="[A-Za-z0-9][A-Za-z0-9_.-]*" placeholder="e.g. custodian-a" onChange={e=>setSource(e.target.value)}/><p id="import-source-help" className={styles.hint}>A short, stable name for the system sending the file. Reuse it for repeat deliveries; each source trade ID identifies one trade within this strategy and source.</p></div>
       <div className={styles.field}><label htmlFor="import-file">Trade file (.xlsx or UTF-8 CSV)</label><div className={styles.fileBox}><input id="import-file" type="file" required accept=".xlsx,.csv" disabled={disabled||!strategy} onChange={e=>setFile(e.target.files?.[0]??null)}/>{file?<span className={styles.fileName}>{file.name} · {(file.size/1024).toFixed(1)} KiB</span>:<span className={styles.hint}>Choose your completed Excel workbook or a compatible UTF-8 CSV.</span>}</div></div>
       <div className={styles.note}><strong>All rows must pass.</strong> If one row is faulty, nothing in the batch is booked. You will get a row-by-row error report.</div>
       <button className={styles.primary} type="submit" disabled={disabled||!options||!strategy||!file}>{busy?'Processing…':'Upload for review — no booking'}</button>
      </section>
     </div></form>:<p className={styles.note}>You can inspect imports within your read scope. Booking permission is required to upload or confirm trades. Open Import history to inspect retained files.</p>}
   </>}
 </main>;
}
