import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {apiRead} from '@/lib/server/api-read';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {WorkspaceShell} from '@/components/workspace-shell';
import {StrategyNavigation,StrategyPositions,StrategyCalendars,type PositionData,type MovementData,type CalendarData} from '@/components/strategy-workspace';
import type {Strategy} from '../strategy-console'; import {StrategyMeasures,type MeasureData,type MeasurePolicy} from '@/components/strategy-measures';
export const dynamic='force-dynamic';

export default async function StrategyDetailPage({params,searchParams}:{params:Promise<{strategyId:string}>;searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const access=await resolveWorkspaceAccess();if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace,context}=access,{strategyId}=await params,input=await searchParams;
 const query=new URLSearchParams();for(const key of ['view','asOf','basis','q','includeClosed','offset','position','movementOffset','informationCutoff','policyId','displayCurrency']){const value=input[key];if(typeof value==='string')query.set(key,value);}
 if(!query.has('asOf'))query.set('asOf',new Date().toISOString().slice(0,10));
 const view=['overview','positions','measures','calendars'].includes(query.get('view')??'')?query.get('view')!:'positions';query.set('view',view);
 const headers={'X-Tenant-Id':context.tenantId,'X-User-Account-Id':context.userAccountId};
 async function read<T>(path:string):Promise<{data?:T;error?:string}>{
  try{const response=await apiRead(new URL(`/v1/${path}`,process.env.REFERENCE_API_URL??'http://localhost:8000'),{headers,cache:'no-store'},fetch,path.includes('/measures?')?60000:undefined);const body=await response.json();
   if(!response.ok){const message=typeof body.detail==='string'?body.detail:typeof body.error?.message==='string'?body.error.message:'The service could not return this information. Check the requested date and filters.';return {error:response.status===403?path.includes('/measures')?'Measures require strategy-scoped valuation read/calculation, trade-read and market-data access.':'You do not have the required permission for this strategy. Positions require TRADE_READ; calendars require CALENDAR_READ.':message};}
   return {data:body};
  }catch{return {error:'The service is unavailable. No empty or zero position is assumed.'};}
 }
 const detail=await read<{data:Strategy}>(`strategies/${encodeURIComponent(strategyId)}`);
 if(!detail.data)return <WorkspaceShell tenantName={workspace.tenantName} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} membershipRole={workspace.membershipRole}><main className="mvp-page"><Link href="/strategies">← Strategies</Link><p role="alert" className="error-panel">{detail.error}</p></main></WorkspaceShell>;
 const strategy=detail.data.data;let measureData:{data?:MeasureData;error?:string}={},measurePolicies:MeasurePolicy[]=[],canCalculateMeasures=false;let positions:{data?:PositionData;error?:string}={},movements:{data?:MovementData;error?:string}={},calendars:{data?:CalendarData;error?:string}={};
 if(view==='positions'){
  const filter=new URLSearchParams();for(const key of ['asOf','basis','q','includeClosed','offset','informationCutoff'])if(query.has(key))filter.set(key,query.get(key)!);
  positions=await read<PositionData>(`strategies/${strategyId}/positions?${filter}`);
  if(query.has('position')&&positions.data){const movementFilter=new URLSearchParams({asOf:query.get('asOf')!,basis:query.get('basis')??'EXECUTED',informationCutoff:positions.data.informationCutoff,offset:query.get('movementOffset')??'0'});movements=await read<MovementData>(`strategies/${strategyId}/positions/${encodeURIComponent(query.get('position')!)}/movements?${movementFilter}`);}
 }
 if(view==='measures'){const options=await read<{policies:MeasurePolicy[];strategies:Array<{id:string;canCalculate:boolean}>}>('valuation/options');if(options.data){measurePolicies=options.data.policies.filter(p=>!p.strategyId||p.strategyId===strategyId);canCalculateMeasures=options.data.strategies.some(s=>s.id===strategyId&&s.canCalculate);if(query.has('policyId')&&canCalculateMeasures){const filter=new URLSearchParams();for(const key of ['asOf','basis','policyId','offset','informationCutoff'])if(query.has(key))filter.set(key,query.get(key)!);measureData=await read<MeasureData>(`strategies/${strategyId}/measures?${filter}`);}}else measureData={error:options.error};} if(view==='calendars')calendars=await read<CalendarData>(`strategies/${strategyId}/calendars?${new URLSearchParams({asOf:query.get('asOf')!})}`);
 return <WorkspaceShell tenantName={workspace.tenantName} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} membershipRole={workspace.membershipRole} sourceLabel="LIVE API"><main className="mvp-page strategy-workspace">
  <header className="mvp-header"><div><Link href="/strategies">← Strategies</Link><p className="eyebrow">{strategy.strategyCode} · {strategy.strategyType.replaceAll('_',' ')}</p><h1>{strategy.displayName}</h1><p className="muted">Base currency {strategy.baseCurrencyCode??'not set'} · {strategy.status}</p></div><span className="strategy-chip">TENANT SCOPED</span></header>
  <StrategyNavigation strategy={strategy} view={view} query={query} canMeasure={workspace.moduleCodes.includes('VALUATION')&&(workspace.permissionCodes??[]).includes('VALUATION_READ')}/>
  {view==='overview'?<section className="strategy-card"><h2>Strategy overview</h2><dl className="strategy-overview"><div><dt>Code</dt><dd>{strategy.strategyCode}</dd></div><div><dt>Operating model</dt><dd>{strategy.strategyType.replaceAll('_',' ')}</dd></div><div><dt>Base currency</dt><dd>{strategy.baseCurrencyCode??'Not set'}</dd></div><div><dt>Status</dt><dd>{strategy.status}</dd></div></dl><p>Positions show booked holdings, not a published valuation or a settlement/accounting balance. Dated cash snapshots remain separate.</p><p><Link href="/tenant-profile/access?view=strategies">Manage strategy access</Link></p></section>:null}
  {view==='measures'?<StrategyMeasures strategyId={strategyId} query={query} policies={measurePolicies} data={measureData.data} error={measureData.error} canCalculate={canCalculateMeasures}/>:null}{view==='positions'?<StrategyPositions strategyId={strategyId} query={query} data={positions.data} error={positions.error} movements={movements.data} movementError={movements.error}/>:null}
  {view==='calendars'?<><form method="get" className="strategy-toolbar"><input type="hidden" name="view" value="calendars"/><label>Inspect date<input type="date" name="asOf" defaultValue={query.get('asOf')!} required/></label><button>Apply</button></form><StrategyCalendars data={calendars.data} error={calendars.error}/></>:null}
 </main></WorkspaceShell>;
}
