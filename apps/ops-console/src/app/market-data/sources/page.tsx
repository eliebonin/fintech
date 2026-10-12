import {MarketDataNavigation} from '@/components/market-data-navigation';
import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {WorkspaceShell} from '@/components/workspace-shell';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {MarketDataSourcesConsole} from '@/components/market-data-sources-console';
export const dynamic='force-dynamic';
export default async function MarketDataSourcesPage(){
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-tenant');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access, enabled=workspace.moduleCodes.includes('MARKET_DATA');
 let catalogue=null;
 try{if(enabled)catalogue=(await(await pricingPolicyClient()).GET('/v1/market-data/sources')).data??null;}catch{/* No synthetic fallback or cross-tenant data. */}
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>
  <main className="mvp-page">{enabled?<MarketDataNavigation active="sources"/>:null}<header className="mvp-header"><div><p className="eyebrow">GOVERNED MARKET DATA</p><h1>Data sources</h1><p>Inspect providers, licensed coverage and source selection priorities for this tenant.</p><Link href="/market-data">Market data</Link> · <Link href="/market-data/policies">Pricing policies</Link></div></header>
   {!enabled?<p className="error-panel">MARKET_DATA is not enabled. Contact your tenant administrator.</p>:catalogue?<MarketDataSourcesConsole initial={catalogue}/>:<p className="error-panel">Source configuration is unavailable. Reload to retry; no fallback configuration is shown.</p>}
  </main>
 </WorkspaceShell>;
}
