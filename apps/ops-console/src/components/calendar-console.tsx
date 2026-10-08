'use client';
import {useRef,useState} from 'react';
import type {FormEvent} from 'react';
import {newCalendarDraft,parseCalendarDates,type CalendarPublish,type CalendarView,type CalendarOptions,type CalendarDays,type CalendarAssignment} from '@/lib/calendar-input';

async function request<T>(url:string,init?:RequestInit):Promise<T> {
 const response=await fetch(url,init),body=await response.json();
 if(!response.ok)throw new Error(body?.error?.message??body?.error?.detail??body?.detail??`Request failed (${response.status}).`);
 return body as T;
}
function label(calendar:CalendarView) {return `${calendar.displayName} · ${calendar.purpose} · ${calendar.tenantOwned?'v'+calendar.versionNo:'Reference'} · ${calendar.calendarId.slice(-8)}`;}

export function CalendarConsole({options:initial}:{options:CalendarOptions}) {
 const [options,setOptions]=useState(initial),[selected,setSelected]=useState<CalendarView|null>(null),[draft,setDraft]=useState(newCalendarDraft);
 const [days,setDays]=useState<CalendarDays|null>(null),[from,setFrom]=useState(draft.coverageFrom),[to,setTo]=useState(draft.coverageTo);
 const [importText,setImportText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const [assignment,setAssignment]=useState<CalendarAssignment>({calendarId:'',targetKind:'STRATEGY',targetId:'',validFrom:draft.coverageFrom,validTo:draft.coverageTo,reason:''});
 const keys=useRef(new Map<string,{payload:string;key:string}>());
 async function publish<T>(endpoint:string,body:unknown):Promise<T> {
  const payload=JSON.stringify(body),previous=keys.current.get(endpoint);
  const key=previous?.payload===payload?previous.key:crypto.randomUUID();keys.current.set(endpoint,{payload,key});
  return request(endpoint,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:payload});
 }
 async function work(action:()=>Promise<void>) {setBusy(true);setError('');setMessage('');try{await action();}catch(caught){setError((caught as Error).message);}finally{setBusy(false);}}
 async function select(id:string) {await work(async()=>{
  const calendar=await request<CalendarView>(`/api/market-data/calendars/${id}`);setSelected(calendar);setDays(null);
  if(calendar.configuration){setDraft(calendar.configuration);setFrom(calendar.coverageFrom!);setTo(calendar.coverageTo!);}
 });}
 async function save(event:FormEvent) {event.preventDefault();await work(async()=>{
  const calendar=await publish<CalendarView>('/api/market-data/calendars',draft);setSelected(calendar);setDays(null);
  setOptions(await request('/api/market-data/calendars/options'));setMessage(`Published version ${calendar.versionNo}. Existing versions and assignments are unchanged.`);
 });}
 async function preview(event:FormEvent) {event.preventDefault();if(!selected)return;await work(async()=>{
  setDays(await request(`/api/market-data/calendars/${selected.calendarId}/days?fromDate=${from}&toDate=${to}`));
 });}
 async function assign(event:FormEvent) {event.preventDefault();await work(async()=>{
  await publish('/api/market-data/calendars/assignments',assignment);setOptions(await request('/api/market-data/calendars/options'));setMessage('Version-pinned assignment recorded. Prior decisions remain available.');
 });}
 return <>
  <section className="history-panel"><h2>Inspect a calendar version</h2><p>Exchange references and tenant schedules are separate. UNKNOWN means unassessed—not an open day.</p>
   <label>Calendar<select disabled={busy} value={selected?.calendarId??''} onChange={e=>{if(e.target.value)void select(e.target.value);}}><option value="">Select…</option>{options.calendars.map(calendar=><option key={calendar.calendarId} value={calendar.calendarId}>{label(calendar)}</option>)}</select></label>
   {selected?<p>{selected.calendarCode} · {selected.timezoneName} · coverage {selected.coverageFrom??'Not declared'} to {selected.coverageTo??'Not declared'}</p>:null}
   <form onSubmit={preview}><fieldset disabled={busy}><legend>Preview saved version</legend><div className="pricing-policy-fields"><label>From<input required type="date" value={from} onChange={e=>{setFrom(e.target.value);setDays(null);}}/></label><label>To<input required type="date" value={to} onChange={e=>{setTo(e.target.value);setDays(null);}}/></label></div><button disabled={!selected}>Preview dates</button></fieldset></form>
   {days?<div className="calendar-days"><table><thead><tr><th>Date</th><th>Status</th><th>Reason and evidence</th></tr></thead><tbody>{days.days.map(day=><tr key={day.date}><td>{day.date}</td><td>{day.status}</td><td><details><summary>{String(day.evidence.reason??'Unassessed')}</summary><pre>{JSON.stringify(day.evidence,null,2)}</pre></details></td></tr>)}</tbody></table></div>:null}
  </section>
  {!options.canManage?<section className="history-panel"><h2>Read-only</h2><p>Publishing and assigning calendars requires a MARKET_DATA tenant administrator.</p></section>:<>
   <form className="history-panel pricing-policy-editor" onSubmit={save}><h2>Publish a tenant calendar version</h2><p>Saving never edits an exchange calendar or automatically replaces an assignment. Removing a holiday means a documented OPEN exception or a revised exception list.</p>
    <fieldset disabled={busy}><legend>Identity, purpose and coverage</legend><div className="pricing-policy-fields">
     <label>Calendar code<input required maxLength={100} value={draft.calendarCode} onChange={e=>setDraft({...draft,calendarCode:e.target.value})}/></label>
     <label>Display name<input required maxLength={250} value={draft.displayName} onChange={e=>setDraft({...draft,displayName:e.target.value})}/></label>
     <label>Purpose<select value={draft.purpose} onChange={e=>setDraft({...draft,purpose:e.target.value as CalendarPublish['purpose']})}>{['VALUATION','DEALING','SETTLEMENT'].map(value=><option key={value}>{value}</option>)}</select></label>
     <label>IANA timezone<input required value={draft.timezoneName} onChange={e=>setDraft({...draft,timezoneName:e.target.value})}/></label>
     <label>Local decision time<input required type="time" step={1} value={draft.decisionTime} onChange={e=>setDraft({...draft,decisionTime:e.target.value})}/></label>
     <label>Coverage from<input required type="date" value={draft.coverageFrom} onChange={e=>setDraft({...draft,coverageFrom:e.target.value})}/></label>
     <label>Coverage to<input required type="date" value={draft.coverageTo} onChange={e=>setDraft({...draft,coverageTo:e.target.value})}/></label>
     <label>Source / administrator notice<input required maxLength={250} value={draft.sourceReference} onChange={e=>setDraft({...draft,sourceReference:e.target.value})}/></label>
     <label>Base rule<select value={draft.mode} onChange={e=>setDraft({...draft,mode:e.target.value as CalendarPublish['mode'],baseCalendarIds:[]})}><option value="WEEKDAYS">Specified weekdays</option><option value="ALL_OPEN">All selected calendars open</option><option value="ANY_OPEN">Any selected calendar open</option><option value="EXPLICIT">Explicit published dated schedule</option></select></label>
    </div>
    {draft.mode==='WEEKDAYS'?<div>{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((name,index)=><label key={name}><input type="checkbox" checked={draft.weekdays?.includes(index)} onChange={e=>setDraft({...draft,weekdays:e.target.checked?[...(draft.weekdays??[]),index]:(draft.weekdays??[]).filter(day=>day!==index)})}/>{name}</label>)}</div>:null}
    {draft.mode==='ALL_OPEN'||draft.mode==='ANY_OPEN'?<label>Required reference calendars (select multiple)<select required multiple value={draft.baseCalendarIds??[]} onChange={e=>setDraft({...draft,baseCalendarIds:Array.from(e.target.selectedOptions,option=>option.value)})}>{options.calendars.filter(c=>!c.tenantOwned||c.purpose===draft.purpose).map(c=><option key={c.calendarId} value={c.calendarId}>{label(c)}</option>)}</select></label>:null}
    {draft.mode==='EXPLICIT'?<p>Only explicitly supplied dates are assessed. Omitted dates remain UNKNOWN.</p>:null}
    </fieldset>
    <fieldset disabled={busy}><legend>Dated exceptions / explicit schedule</legend>
     {(draft.exceptions??[]).map((entry,index)=><div className="pricing-policy-fields" key={index}><label>Date<input required type="date" value={entry.date} onChange={e=>setDraft({...draft,exceptions:draft.exceptions!.map((v,i)=>i===index?{...v,date:e.target.value}:v)})}/></label><label>Decision<select value={entry.status} onChange={e=>setDraft({...draft,exceptions:draft.exceptions!.map((v,i)=>i===index?{...v,status:e.target.value as 'OPEN'|'CLOSED'}:v)})}><option>OPEN</option><option>CLOSED</option></select></label><label>Reason<input required maxLength={500} value={entry.reason} onChange={e=>setDraft({...draft,exceptions:draft.exceptions!.map((v,i)=>i===index?{...v,reason:e.target.value}:v)})}/></label><label>Source<input required maxLength={250} value={entry.sourceReference} onChange={e=>setDraft({...draft,exceptions:draft.exceptions!.map((v,i)=>i===index?{...v,sourceReference:e.target.value}:v)})}/></label><button type="button" onClick={()=>setDraft({...draft,exceptions:draft.exceptions!.filter((_,i)=>i!==index)})}>Remove draft exception</button></div>)}
     <button type="button" disabled={(draft.exceptions?.length??0)>=1100} onClick={()=>setDraft({...draft,exceptions:[...(draft.exceptions??[]),{date:draft.coverageFrom,status:'CLOSED',reason:'',sourceReference:draft.sourceReference}]})}>Add date exception</button>
     <details><summary>Import dated schedule text</summary><label>One row per date: YYYY-MM-DD | OPEN or CLOSED | reason | source<textarea rows={4} value={importText} onChange={e=>setImportText(e.target.value)}/></label><button type="button" onClick={()=>{try{setDraft({...draft,exceptions:parseCalendarDates(importText)});setError('');}catch(caught){setError((caught as Error).message);}}}>Replace draft dates from text</button></details>
    </fieldset><button disabled={busy}>Publish immutable version</button>
   </form>
   <form className="history-panel" onSubmit={assign}><h2>Assign pinned version</h2><p>Purpose comes from the calendar. Reassignment retains the same effective interval; adjacent intervals can use different versions. Dealing and settlement schedules do not alter price selection.</p><fieldset disabled={busy}><legend>Assignment decision</legend><div className="pricing-policy-fields">
    <label>Published tenant version<select required value={assignment.calendarId} onChange={e=>{const c=options.calendars.find(c=>c.calendarId===e.target.value);setAssignment({...assignment,calendarId:e.target.value,validFrom:c?.coverageFrom??assignment.validFrom,validTo:c?.coverageTo??assignment.validTo});}}><option value="">Select…</option>{options.calendars.filter(c=>c.tenantOwned).map(c=><option key={c.calendarId} value={c.calendarId}>{label(c)}</option>)}</select></label>
    <label>Target kind<select value={assignment.targetKind} onChange={e=>setAssignment({...assignment,targetKind:e.target.value as CalendarAssignment['targetKind'],targetId:''})}><option value="STRATEGY">Strategy</option><option value="FUND_REFERENCE">Fund / share-class reference</option></select></label>
    {assignment.targetKind==='STRATEGY'?<label>Strategy<select required value={assignment.targetId} onChange={e=>setAssignment({...assignment,targetId:e.target.value})}><option value="">Select…</option>{options.strategies.map(s=><option key={s.id} value={s.id}>{s.label} · {s.id.slice(-8)}</option>)}</select></label>:<label>Fund or share-class UUID<input required value={assignment.targetId} onChange={e=>setAssignment({...assignment,targetId:e.target.value})}/></label>}
    <label>Effective from<input required type="date" value={assignment.validFrom} onChange={e=>setAssignment({...assignment,validFrom:e.target.value})}/></label><label>Effective to<input required type="date" value={assignment.validTo} onChange={e=>setAssignment({...assignment,validTo:e.target.value})}/></label><label>Assignment reason<input required maxLength={500} value={assignment.reason} onChange={e=>setAssignment({...assignment,reason:e.target.value})}/></label>
   </div><button>Assign pinned version</button></fieldset></form>
  </>}
  <section className="history-panel"><h2>Assignment history</h2><p>Latest recorded decision for the same target, purpose and interval applies at the requested information cutoff. No silent switch to a newer calendar version.</p>{options.assignments.length?options.assignments.map(a=><p key={a.assignmentId}>{a.targetKind} {a.targetId} · {a.purpose} · {a.validFrom}–{a.validTo} · calendar {a.calendarId} · {a.reason} · recorded {a.createdAtUtc}</p>):<p>No assignments recorded.</p>}</section>
  {error?<p role="alert" className="error-panel">{error}</p>:null}{message?<p role="status">{message}</p>:null}
 </>;
}
