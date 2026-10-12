import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {WorkspaceShell} from '@/components/workspace-shell';
import {MarketDataNavigation} from '@/components/market-data-navigation';
import {MarketDataCoverage} from '@/components/market-data-coverage';
export const dynamic='force-dynamic';
export default async function CoveragePage({searchParams}:{searchParams:Promise<{references?:string;valuationDate?:string}>}){
 const query=await searchParams,access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-tenant');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access,enabled=workspace.moduleCodes.includes('MARKET_DATA');
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page">
  {enabled?<MarketDataNavigation active="coverage"/>:null}
  <header className="mvp-header"><div><p className="eyebrow">MARKET DATA / REQUIRED INPUTS</p><h1>Coverage and exceptions</h1><p>Check the prices required for an explicit set of references under a chosen policy, date and information cutoff.</p></div></header>
  {enabled?<MarketDataCoverage key={workspace.tenantId} tenantId={workspace.tenantId} initialReferences={(query.references??'').slice(0,2000)} initialDate={query.valuationDate??new Date().toISOString().slice(0,10)} initialCutoff={new Date().toISOString().slice(0,16)}/>:<p className="error-panel">Market data is not enabled. Contact your tenant administrator.</p>}
 </main></WorkspaceShell>;
}
