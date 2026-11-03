'use client';
import {useEffect,useState} from 'react';
import {WorkspaceTabs,WorkspaceTabPanel} from '@/components/workspace-navigation';
import {EntityForm,firmCategories} from './entity-form';
import {CandidateInspector} from './candidate-inspector';
import {reportingRequest,saveFile} from './transport';
import {reportingLabel,exactQuantity,type Profile,type Candidate,type Totals,type Scope,type Artifact} from './presentation';
type Options={profiles:Profile[];strategies:{id:string;name:string}[]};
type Queue={items:Candidate[];total:number;totals:Totals};
type ExportRow={exportId:string;recordedAt:string;profileName:string;fromDate:string;toDate:string;totals:Totals};
type Preview={expectedRevisions:Record<string,number>;totals:Totals};
const emptyTotals:Totals={total:0,included:0,held:0,notReportable:0,attention:0};
function TotalsView({totals}:{totals:Totals}){return <dl className="reg-counts">{Object.entries({total:'Prepared',included:'Ready for export',attention:'Needs attention',held:'Held',notReportable:'Not reportable'}).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{totals[key as keyof Totals]}</dd></div>)}</dl>;}
export function ReportingWorkspace({permissions}:{permissions:string[]}){
 const can=(p:string)=>permissions.includes(p);
 const [tab,setTab]=useState('preparation');const [options,setOptions]=useState<Options>({profiles:[],strategies:[]});
 const [scope,setScope]=useState<Scope>({profileId:'',strategyId:'',fromDate:new Date().toISOString().slice(0,10),toDate:new Date().toISOString().slice(0,10)});
 const [status,setStatus]=useState('ALL');const [limit,setLimit]=useState(25);const [offset,setOffset]=useState(0);
 const [queue,setQueue]=useState<Queue|null>(null);const [queueKey,setQueueKey]=useState('');
 const [selected,setSelected]=useState<Candidate|null>(null);const [entity,setEntity]=useState<Profile|'new'|null>(null);
 const [exports,setExports]=useState<{items:ExportRow[];total:number}>({items:[],total:0});const [historyOffset,setHistoryOffset]=useState(0);
 const [preview,setPreview]=useState<{scope:Scope;data:Preview;key:string}|null>(null);const [artifact,setArtifact]=useState<Artifact|null>(null);
 const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [refresh,setRefresh]=useState(0);
 const query=new URLSearchParams({...scope,status,limit:String(limit),offset:String(offset)}).toString();
 const hasScope=Boolean(scope.profileId&&scope.strategyId&&scope.fromDate&&scope.toDate&&scope.fromDate<=scope.toDate);
 useEffect(()=>{const controller=new AbortController();
  reportingRequest<Options>('options',undefined,undefined,controller.signal).then(setOptions).catch(e=>{if(!controller.signal.aborted)setError(e.message);});return()=>controller.abort();
 },[refresh]);
 useEffect(()=>{if(!hasScope)return;const controller=new AbortController();setLoading(true);
  reportingRequest<Queue>('candidates?'+query,undefined,undefined,controller.signal).then(data=>{setQueue(data);setQueueKey(query);})
   .catch(e=>{if(!controller.signal.aborted)setError(e.message);}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[query,hasScope,refresh]);
 useEffect(()=>{if(tab!=='history')return;const controller=new AbortController();
  reportingRequest<{items:ExportRow[];total:number}>('exports?limit=25&offset='+historyOffset,undefined,undefined,controller.signal).then(setExports)
   .catch(e=>{if(!controller.signal.aborted)setError(e.message);});return()=>controller.abort();
 },[tab,refresh,historyOffset]);
 const visible=queueKey===query?queue:null;
 function updateScope(name:keyof Scope,value:string){setScope(current=>({...current,[name]:value}));setOffset(0);setSelected(null);setPreview(null);setError('');setNotice('');}
 async function operation(fn:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await fn();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function prepare(){await operation(async()=>{const data=await reportingRequest<{created:number;changed:number;examined:number}>('prepare',scope);setRefresh(x=>x+1);setPreview(null);setSelected(null);setNotice(`Examined ${data.examined} executions: ${data.created} new, ${data.changed} changed. Unresolved reports remain visible.`);});}
 async function inspect(row:Candidate){await operation(async()=>{setSelected(await reportingRequest<Candidate>('candidates/'+row.candidateId));});}
 async function previewExport(){await operation(async()=>{const data=await reportingRequest<Preview>('export-preview?'+new URLSearchParams(scope));setPreview({scope:{...scope},data,key:crypto.randomUUID()});});}
 async function freeze(){if(!preview)return;await operation(async()=>{const result=await reportingRequest<Artifact>('exports',{...preview.scope,expectedRevisions:preview.data.expectedRevisions},preview.key);setArtifact(result);setPreview(null);setRefresh(x=>x+1);setNotice('Preparation export retained. It has not been submitted to or accepted by the FCA.');});}
 async function openExport(id:string){await operation(async()=>{setArtifact(await reportingRequest<Artifact>('exports/'+id));});}
 async function downloadArtifact(kind:'csv'|'manifest'){if(!artifact)return;await operation(async()=>{
  const current=await reportingRequest<Artifact>('exports/'+artifact.exportId);
  saveFile(kind==='csv'?`uk-mifir-preparation-${current.exportId}.csv`:`uk-mifir-evidence-${current.exportId}.json`,
   kind==='csv'?current.csvContent:JSON.stringify(current.manifest,null,2),kind==='csv'?'text/csv;charset=utf-8':'application/json');
 });}
 return <>
  <div className="reg-notice"><strong>UK transaction reporting · preparation workspace</strong><p>Assess and review execution reports. Exports are preparation data; official field/schema validation and submission connectivity are not yet enabled.</p></div>
  <WorkspaceTabs id="reporting" label="Regulatory Reporting" items={[{id:'preparation',label:'Transaction preparation'},{id:'entities',label:'Reporting entities'},{id:'history',label:'Export history'}]} value={tab} onChange={setTab}/>
  {error?<div className="error-panel" role="alert">{error}<button type="button" disabled={busy} onClick={()=>{setError('');setRefresh(x=>x+1);}}>Reload current state</button></div>:null}
  {notice?<p role="status">{notice}</p>:null}
  <WorkspaceTabPanel id="reporting" tab="preparation" value={tab}>
   <section className="reg-card"><h2>Choose reporting scope</h2><fieldset disabled={busy} className="reg-form-grid"><legend>Entity, strategy and execution dates (UTC)</legend>
    <label>Reporting entity<select value={scope.profileId} onChange={e=>updateScope('profileId',e.target.value)}><option value="">Choose an entity</option>{options.profiles.map(p=><option key={p.profileId} value={p.profileId}>{p.name} · v{p.revision}</option>)}</select></label>
    <label>Strategy<select value={scope.strategyId} onChange={e=>updateScope('strategyId',e.target.value)}><option value="">Choose a strategy</option>{options.strategies.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
    <label>From execution date<input type="date" value={scope.fromDate} onChange={e=>updateScope('fromDate',e.target.value)}/></label>
    <label>To execution date<input type="date" value={scope.toDate} onChange={e=>updateScope('toDate',e.target.value)}/></label>
   </fieldset>
   {!options.profiles.length?<p>Add a reporting entity in Reporting entities. A tenant or strategy is not automatically the reporting firm.</p>:null}
   {!options.strategies.length?<p>No strategies are readable with your reporting permissions. Your tenant administrator can review group strategy access.</p>:null}
   <div className="ticket-actions">{can('REPORTING_PREPARE')?<button disabled={busy||!hasScope} onClick={prepare}>Prepare / refresh executions</button>:null}
    {can('REPORTING_EXPORT')?<button disabled={busy||!hasScope||!visible?.totals.included} onClick={previewExport}>Review preparation export</button>:null}</div>
   </section>
   {hasScope?<><TotalsView totals={visible?.totals??emptyTotals}/><section className="reg-card"><div className="reg-heading"><h2>Execution reports</h2><label>Show<select disabled={busy} value={status} onChange={e=>{setStatus(e.target.value);setOffset(0);setSelected(null);}}>{[['ALL','All prepared'],['READY','Ready for export'],['NEEDS_ATTENTION','Needs attention'],['HELD','Held'],['NOT_REPORTABLE','Not reportable']].map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label></div>
    <p className="muted">Ready means local preparation checks passed. Scope decisions, required regulatory fields and final submission validation remain distinct.</p>
    {loading?<p role="status">Loading execution reports…</p>:null}
    <div className="reg-table-wrap"><table><thead><tr><th>Instrument / execution</th><th>Quantity / price</th><th>Reportability</th><th>Preparation</th><th>Export inclusion</th><th>Review</th></tr></thead><tbody>{visible?.items.map(row=><tr key={row.candidateId}><td><strong>{row.facts.instrumentName}</strong><small>{row.facts.instrumentType} · {row.facts.executionTime}</small></td><td>{exactQuantity(row.facts.quantity)} {row.facts.quantityUnit}<small>{exactQuantity(row.facts.executionPrice)} {row.facts.priceCurrency}</small></td><td>{reportingLabel(row.reportability)}</td><td>{reportingLabel(row.readiness)}{row.needsReassessment?<small>Source changed — reassess</small>:null}</td><td>{row.disposition==='HOLD'?'Held':row.included?'Included when exported':'Not included'}</td><td><button type="button" disabled={busy} onClick={()=>inspect(row)}>Inspect</button></td></tr>)}</tbody></table></div>
    {visible&&!visible.items.length?<p>No reports match this selection. Prepare executions or adjust the dates/filter.</p>:null}
    <div className="reg-pagination"><label>Rows<select value={limit} onChange={e=>{setLimit(Number(e.target.value));setOffset(0);}}>{[25,50,100].map(n=><option key={n}>{n}</option>)}</select></label><span>{visible?.total?`${offset+1}–${Math.min(offset+limit,visible.total)} of ${visible.total}`:'0 reports'}</span><button disabled={busy||offset===0} onClick={()=>setOffset(Math.max(0,offset-limit))}>Previous</button><button disabled={busy||!visible||offset+limit>=visible.total} onClick={()=>setOffset(offset+limit)}>Next</button></div>
   </section></>:<p>Choose a reporting entity, strategy and valid date range to view or prepare executions.</p>}
   {selected?<CandidateInspector key={selected.candidateId+':'+selected.revision} row={selected} canReview={can('REPORTING_REVIEW')} onClose={()=>setSelected(null)} onSaved={()=>{setSelected(null);setPreview(null);setRefresh(x=>x+1);setNotice('Reviewed revision saved.');}}/>:null}
   {preview?<section className="reg-card"><h2>Review complete export population</h2><TotalsView totals={preview.data.totals}/><p>All ready reports in this entity/strategy/date scope will be included, across every page. Held and incomplete reports stay outstanding. This export does not establish that reporting for the day is complete.</p><div className="ticket-actions"><button disabled={busy||!Object.keys(preview.data.expectedRevisions).length} onClick={freeze}>Freeze preparation export ({Object.keys(preview.data.expectedRevisions).length})</button><button disabled={busy} onClick={()=>setPreview(null)}>Cancel</button></div></section>:null}
  </WorkspaceTabPanel>
  <WorkspaceTabPanel id="reporting" tab="entities" value={tab}>
   <section className="reg-card"><div className="reg-heading"><h2>Reporting entities</h2>{can('REPORTING_CONFIGURE')?<button onClick={()=>setEntity('new')}>Add entity</button>:null}</div><p>Keep the reporting legal entity separate from funds and trading strategies. Classification and scope require your firm’s assessment.</p>
    {options.profiles.map(p=><article key={p.profileId} className="reg-entity"><div><strong>{p.name}</strong><small>{p.lei} · {firmCategories[p.firmCategory as keyof typeof firmCategories]} · {reportingLabel(p.firmScope)} · v{p.revision}</small></div>{can('REPORTING_CONFIGURE')?<button onClick={()=>setEntity(p)}>Edit</button>:null}</article>)}
    {!options.profiles.length?<p>No reporting entities configured.</p>:null}</section>
   {entity?<EntityForm key={entity==='new'?'new':entity.profileId+entity.revision} profile={entity==='new'?undefined:entity} onCancel={()=>setEntity(null)} onSaved={()=>{setEntity(null);setRefresh(x=>x+1);setPreview(null);}}/>:null}
  </WorkspaceTabPanel>
  <WorkspaceTabPanel id="reporting" tab="history" value={tab}><section className="reg-card"><h2>Retained preparation exports</h2><p>Exported is not submitted or accepted. Download permissions are checked again against the export’s strategy.</p>
   <div className="reg-table-wrap"><table><thead><tr><th>Created</th><th>Reporting entity</th><th>Execution dates</th><th>Included / held / attention</th><th>Evidence</th></tr></thead><tbody>{exports.items.map(e=><tr key={e.exportId}><td>{e.recordedAt}</td><td>{e.profileName}</td><td>{e.fromDate} — {e.toDate}</td><td>{e.totals.included} / {e.totals.held} / {e.totals.attention}</td><td>{can('REPORTING_EXPORT')?<button disabled={busy} onClick={()=>openExport(e.exportId)}>Open export</button>:'Reporting export permission required'}</td></tr>)}</tbody></table></div>
   {!exports.items.length?<p>No retained exports in your accessible strategy scope.</p>:null}
   <div className="reg-pagination"><span>{exports.total} exports</span><button disabled={historyOffset===0||busy} onClick={()=>setHistoryOffset(Math.max(0,historyOffset-25))}>Previous exports</button><button disabled={historyOffset+25>=exports.total||busy} onClick={()=>setHistoryOffset(historyOffset+25)}>Next exports</button></div>
  </section></WorkspaceTabPanel>
  {artifact?<section className="reg-card"><div className="reg-heading"><h2>Frozen preparation export</h2><button aria-label="Close export" onClick={()=>setArtifact(null)}>×</button></div><p>Preparation only · Not submitted · Not regulator-validated</p><div className="ticket-actions"><button disabled={busy} onClick={()=>downloadArtifact('csv')}>Download preparation CSV</button><button disabled={busy} onClick={()=>downloadArtifact('manifest')}>Download evidence manifest</button></div><details><summary>Content proof</summary><p className="reg-proof">SHA-256: {artifact.contentHash}</p></details></section>:null}
 </>;
}
