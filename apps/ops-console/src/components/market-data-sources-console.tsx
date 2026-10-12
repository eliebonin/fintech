'use client';
import {useRef,useState} from 'react';
import {Alert,Box,Button,Chip,FormControl,InputLabel,MenuItem,Paper,Select,Stack,Tab,Tabs,Typography} from '@mui/material';
import {initialOrder,moveSource,type SourceCatalogue,type SourceCommand,type SourcePriority} from '@/lib/market-data-sources';

export function MarketDataSourcesConsole({initial}:{initial:SourceCatalogue}){
 const [catalogue,setCatalogue]=useState(initial),[tab,setTab]=useState(0),[type,setType]=useState(initial.instrumentTypes[0]?.id??''),[scope,setScope]=useState<'TENANT'|'PLATFORM'>('TENANT');
 const [refreshError,setRefreshError]=useState(''),[locked,setLocked]=useState(false),[generation,setGeneration]=useState(0),[notice,setNotice]=useState('');
 async function reload(){
  try{const response=await fetch('/api/market-data/sources',{cache:'no-store'});if(!response.ok)throw new Error();setCatalogue(await response.json());setRefreshError('');setLocked(false);setGeneration(value=>value+1);}
  catch{setRefreshError('Could not reload configuration. Keep the frozen request and retry later.');}
 }
 const tenant=catalogue.priorities.find(p=>p.instrumentTypeId===type&&p.scope==='TENANT');
 const platform=catalogue.priorities.find(p=>p.instrumentTypeId===type&&p.scope==='PLATFORM');
 const saved=scope==='TENANT'?tenant:platform;
 const inherited=scope==='TENANT'&&(!tenant||tenant.mode==='INHERIT');
 const effective=inherited?platform:saved;
 return <Stack spacing={3}>
  <Alert severity="info">Priorities choose among eligible sources. They do not grant licensing rights or change pricing times, price validation, or frozen valuation evidence.</Alert>
  <Tabs value={tab} onChange={(_,value)=>setTab(value)} aria-label="Market data source settings">
   <Tab disabled={locked} label="Providers & scope" id="sources-tab-0" aria-controls="sources-panel-0"/>
   <Tab disabled={locked} label="Source priorities" id="sources-tab-1" aria-controls="sources-panel-1"/>
  </Tabs>
  <Box role="tabpanel" id={`sources-panel-${tab}`} aria-labelledby={`sources-tab-${tab}`}>
   {tab===0?<Stack spacing={2}>
    <Typography>Only currently entitled datasets are shown. A provider is the delivery identity; coverage packages identify the content owner and licensed market.</Typography>
    {!catalogue.sources.length&&<Alert severity="warning">No active source entitlements. Contact your tenant administrator.</Alert>}
    {catalogue.sources.map(source=><Paper variant="outlined" key={source.datasetId} sx={{p:3}}>
     <Stack spacing={1}>
      <Typography variant="overline">{source.provider} / {source.product}</Typography>
      <Typography variant="h6" component="h2">{source.label}</Typography>
      <Stack direction="row" spacing={1} useFlexGap sx={{flexWrap:'wrap'}}><Chip size="small" label={source.tenantOwned?'Tenant-owned source':'Shared source'}/><Chip size="small" label={source.coverageMode==='SCOPED'?'Scoped coverage':source.coverageMode==='MIXED'?'Coverage differs by purpose':'Dataset-wide coverage'}/><Chip size="small" color={source.nonDisplayAllowed?'success':'warning'} label={!source.purposes.includes('VALUATION')?'No valuation entitlement':source.nonDisplayAllowed?'Non-display permitted':'Non-display not permitted'}/></Stack>
      <Typography variant="body2">{source.coverageDescription??'No coverage description provided.'}</Typography>
      <Typography variant="body2">Purposes: {[...new Set(source.purposes)].join(', ')} · Dataset effective {source.validFrom} to {source.validTo??'open-ended'}</Typography>
      <Box component="details"><Typography component="summary" sx={{cursor:'pointer'}}>Coverage details and dataset identifier</Typography>
       <Typography variant="body2" sx={{mt:1}}>Dataset: {source.code} · {source.datasetId}</Typography>
       {source.entitlementScopes.map((grant,index)=><Typography variant="body2" sx={{mt:1}} key={`${grant.purpose}:${index}`}>{grant.purpose}: {grant.coverageMode==='DATASET'?'Dataset-wide':`Scoped to ${grant.packageCodes.join(', ')||'no active packages'}`} · entitlement {grant.validFrom} to {grant.validTo??'open-ended'}</Typography>)}
       {source.packages.length?source.packages.map(p=><Typography variant="body2" key={p.code} sx={{mt:1}}>{p.label} ({p.code}) · Owner: {p.contentOwner} · Market: {p.market??'Not specified'} · {p.timing} · {p.validFrom} to {p.validTo??'open-ended'}</Typography>):<Typography variant="body2" sx={{mt:1}}>{source.coverageMode==='SCOPED'?'No active package grants; series selection is blocked.':'No reviewed package breakdown. Dataset-wide entitlement applies; this is not proof of coverage for every instrument.'}</Typography>}
      </Box>
     </Stack>
    </Paper>)}
   </Stack>:<Stack spacing={2}>
    <Stack direction={{xs:'column',sm:'row'}} spacing={2}>
     <FormControl sx={{minWidth:240}}><InputLabel id="priority-type-label">Instrument type</InputLabel><Select disabled={locked} labelId="priority-type-label" label="Instrument type" value={type} onChange={e=>{setType(e.target.value);setNotice('');}}>{catalogue.instrumentTypes.map(t=><MenuItem value={t.id} key={t.id}>{t.label}</MenuItem>)}</Select></FormControl>
     {catalogue.canManagePlatform&&<FormControl sx={{minWidth:240}}><InputLabel id="priority-scope-label">Configuration scope</InputLabel><Select disabled={locked} labelId="priority-scope-label" label="Configuration scope" value={scope} onChange={e=>setScope(e.target.value as 'TENANT'|'PLATFORM')}><MenuItem value="TENANT">Tenant override</MenuItem><MenuItem value="PLATFORM">Platform defaults</MenuItem></Select></FormControl>}
    </Stack>
    <Paper variant="outlined" sx={{p:3}}><Typography variant="h6" component="h2">Effective selection order</Typography>
     <Typography>{effective?`${inherited?'Inherited platform defaults':scope==='PLATFORM'?'Platform defaults':'Tenant override'} · version ${effective.versionNo} · ${effective.createdAt}`:'Unconfigured — existing policy arbitration applies. The suggested draft below is not active.'}</Typography>
     {effective&&<SourceOrder order={effective.datasetIds} sources={catalogue.sources}/>}
    </Paper>
    <Typography variant="body2">New selections use configuration known by their information cutoff. Explicit policy dataset rules still pin their source, but cannot bypass exclusions. Freshness and pricing conventions remain mandatory.</Typography>
    {notice&&<Alert severity="success">{notice}</Alert>}
    {(scope==='TENANT'?catalogue.canManage:catalogue.canManagePlatform)&&type?<PriorityEditor key={`${generation}:${scope}:${type}:${saved?.versionId??'new'}`} type={type} scope={scope} saved={saved} catalogue={catalogue} lock={setLocked} onSaved={version=>{setLocked(false);setNotice('Saved. New selections use this version; existing run evidence is unchanged.');setCatalogue(current=>({...current,priorities:[...current.priorities.filter(p=>!(p.instrumentTypeId===version.instrumentTypeId&&p.scope===version.scope)),version]}));}} reload={reload}/>:<Alert severity="info">Read-only configuration. A tenant administrator with MARKET_DATA access can change tenant priorities; only a platform administrator can change platform defaults.</Alert>}
   </Stack>}
  </Box>
  {!catalogue.canManage&&tab===0&&<Typography variant="body2">Read-only: contact a tenant administrator to change source priorities.</Typography>}
  {refreshError&&<Alert severity="error">{refreshError}</Alert>}
 </Stack>;
}

function SourceOrder({order,sources}:{order:string[];sources:SourceCatalogue['sources']}){
 return order.length?<Box component="ol">{order.map(id=><li key={id}>{sources.find(s=>s.datasetId===id)?.label??'Unavailable source — not entitled or no longer active'}</li>)}</Box>:<Alert severity="warning" sx={{mt:2}}>All sources excluded for this instrument type.</Alert>;
}

function PriorityEditor({type,scope,saved,catalogue,onSaved,reload,lock}:{type:string;scope:'TENANT'|'PLATFORM';saved:SourcePriority|undefined;catalogue:SourceCatalogue;onSaved:(value:SourcePriority)=>void;reload:()=>Promise<void>;lock:(value:boolean)=>void}){
 const available=catalogue.sources.filter(s=>s.purposes.includes('VALUATION')&&(scope!=='PLATFORM'||!s.tenantOwned));
 const [order,setOrder]=useState(()=>initialOrder(available,saved?.mode==='CUSTOM'?saved.datasetIds:null));
 const [add,setAdd]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [pending,setPending]=useState<{key:string;body:SourceCommand}|null>(null),[conflict,setConflict]=useState(false);
 const inFlight=useRef(false);
 async function save(mode:'CUSTOM'|'INHERIT'){
  if(inFlight.current)return;
  const frozen=pending??{key:crypto.randomUUID(),body:{instrumentTypeId:type,scope,mode,datasetIds:mode==='CUSTOM'?order:[],expectedVersionId:saved?.versionId??null}};
  setPending(frozen);lock(true);inFlight.current=true;setBusy(true);setError('');setNotice('');
  try{
   const response=await fetch('/api/market-data/sources',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':frozen.key},body:JSON.stringify(frozen.body)});
   const result=await response.json();
   if(!response.ok){setConflict(response.status===409);setError(result?.detail??result?.error?.detail??result?.error?.message??'Source priorities could not be saved.');if(response.status>=400&&response.status<500&&response.status!==409){setPending(null);lock(false);}return;}
   onSaved(result);setPending(null);setNotice('Saved. New selections use this version; existing run evidence is unchanged.');
  }catch{setError('Save outcome is uncertain. Retry the unchanged request with the same key, or reload before editing.');}
  finally{inFlight.current=false;setBusy(false);}
 }
 return <Paper variant="outlined" sx={{p:3}}><Stack spacing={2}>
  <Typography variant="h6" component="h2">{scope==='TENANT'?'Tenant priority override':'Platform default priorities'}</Typography>
  <Typography variant="body2">Rank 1 is preferred among eligible prices for the same market date. Sources omitted from a saved custom order are excluded. Tenant-owned sources are suggested first, not automatically activated.</Typography>
  <Box component="fieldset" disabled={busy||!!pending} sx={{border:0,p:0,m:0}}><Stack spacing={1}>
   {order.map((id,index)=>{const source=available.find(s=>s.datasetId===id);return <Stack key={id} direction={{xs:'column',sm:'row'}} spacing={1} sx={{alignItems:{sm:'center'}}}>
    <Typography sx={{flex:1}}>{index+1}. {source?`${source.provider} — ${source.label}`:'Unavailable source — remove before saving'}{source&&!source.nonDisplayAllowed?' (non-display permission missing)':''}</Typography>
    <Button size="small" disabled={index===0||busy||!!pending} aria-label={`Move ${source?.label??'unavailable source'} up`} onClick={()=>setOrder(moveSource(order,id,-1))}>Move up</Button>
    <Button size="small" disabled={index===order.length-1||busy||!!pending} aria-label={`Move ${source?.label??'unavailable source'} down`} onClick={()=>setOrder(moveSource(order,id,1))}>Move down</Button>
    <Button size="small" disabled={busy||!!pending} onClick={()=>setOrder(order.filter(d=>d!==id))}>Exclude</Button>
   </Stack>;})}
   {!order.length&&<Alert severity="warning">Saving this empty custom order excludes every source for this instrument type.</Alert>}
   <Stack direction={{xs:'column',sm:'row'}} spacing={1} sx={{pt:2}}><FormControl sx={{minWidth:260}}><InputLabel id="add-source-label">Add a source</InputLabel><Select labelId="add-source-label" label="Add a source" value={add} disabled={busy||!!pending} onChange={e=>setAdd(e.target.value)}>{available.filter(s=>!order.includes(s.datasetId)).map(s=><MenuItem key={s.datasetId} value={s.datasetId}>{s.provider} — {s.label}</MenuItem>)}</Select></FormControl><Button disabled={!add||busy||!!pending} onClick={()=>{setOrder([...order,add]);setAdd('');}}>Add to order</Button></Stack>
  </Stack></Box>
  {error&&<Alert severity="error" role="alert">{error}</Alert>}{notice&&<Alert severity="success">{notice}</Alert>}
  <Stack direction={{xs:'column',sm:'row'}} spacing={1}>
   {!pending?<><Button variant="contained" onClick={()=>save('CUSTOM')} disabled={busy}>{scope==='TENANT'?'Save tenant priorities':'Save platform defaults'}</Button>{scope==='TENANT'&&<Button onClick={()=>save('INHERIT')} disabled={busy}>Restore platform inheritance</Button>}</>:<><Button variant="contained" onClick={()=>save(pending.body.mode??'CUSTOM')} disabled={busy||conflict}>{busy?'Saving…':'Retry unchanged'}</Button><Button disabled={busy} onClick={reload}>Reload configuration</Button></>}
  </Stack>
 </Stack></Paper>;
}
