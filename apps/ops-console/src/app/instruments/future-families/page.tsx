import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {FutureFamilyForm} from '@/components/future-family-form';
import {getActiveTenantContext,getActiveTenantWorkspace} from '@/lib/tenant-session';
import {listCurrencies} from '@/lib/reference-api-client';
export const dynamic='force-dynamic';
export default async function FamiliesPage({searchParams}:{searchParams:Promise<{view?:string}>}){
  let context,workspace;try{[context,workspace]=await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]);}catch{redirect('/select-tenant');}
  if(workspace.membershipRole!=='TENANT_ADMIN'||!workspace.moduleCodes.includes('TRADING'))redirect('/instruments');
  const shell={tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try{const currencies=(await listCurrencies(context,['REGULAR','CRYPTO'])).data;return <WorkspaceShell {...shell}><main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">FAMILY → EXPIRY → LISTING</p><h1>Futures families</h1><p className="muted">Define the reusable product specification first. Individual expiries and venue listings follow approval.</p></div></header><FutureFamilyForm tenantId={context.tenantId} currencies={currencies} browse={(await searchParams).view==='browse'}/></main></WorkspaceShell>;}catch{return <WorkspaceShell {...shell}><main className="mvp-page"><h1>Futures families</h1><p role="alert">Currency catalogue unavailable. Try again later.</p></main></WorkspaceShell>;}
}
