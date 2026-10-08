import Link from 'next/link';
import {redirect} from 'next/navigation';
import {getActiveTenantContext,getActiveTenantWorkspace} from '@/lib/tenant-session';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {WorkspaceShell} from '@/components/workspace-shell';
import {PricingPolicyConsole} from '@/components/pricing-policy-console';
export const dynamic='force-dynamic';
export default async function PricingPoliciesPage() {
 try{await getActiveTenantContext();}catch{redirect('/select-tenant');}
 const workspace=await getActiveTenantWorkspace(),enabled=workspace.moduleCodes.includes('MARKET_DATA');
 const client=enabled?await pricingPolicyClient():null;
 let options=null,policies=null;
 try {if(client){const [o,p]=await Promise.all([client.GET('/v1/market-data/valuation-policy-options'),client.GET('/v1/market-data/valuation-policies',{params:{query:{valuationDate:new Date().toISOString().slice(0,10)}}})]);options=o.data;policies=p.data;}}catch{/* Explicit unavailability; never use a demo fallback. */}
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">MARKET DATA INPUT SELECTION</p><h1>Pricing policies</h1><p>Combine exchange closes and separate FX fixings under one reproducible information cutoff.</p><Link href="/market-data">Back to Market data</Link></div></header>
  {!enabled?<p className="error-panel">MARKET_DATA is not enabled. Contact your tenant administrator.</p>:options&&policies?<PricingPolicyConsole options={options} initialPolicies={policies}/>:<p className="error-panel">Policy configuration is unavailable. No fallback tenant or price is used.</p>}
 </main></WorkspaceShell>;
}
