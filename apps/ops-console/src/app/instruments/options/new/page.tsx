import { redirect } from 'next/navigation';
import { WorkspaceShell } from '@/components/workspace-shell';
import { getActiveTenantContext,getActiveTenantWorkspace } from '@/lib/tenant-session';
import { listCurrencies } from '@/lib/reference-api-client';
import OptionForm from './form';
export const dynamic='force-dynamic';
export default async function NewOptionPage() {
  let context,workspace;try{[context,workspace]=await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]);}catch{redirect('/select-tenant');}
  if(workspace.membershipRole!=='TENANT_ADMIN'||!workspace.moduleCodes.includes('TRADING'))redirect('/instruments');
  let currencies;try{currencies=(await listCurrencies(context,['REGULAR'])).data;}catch{return <WorkspaceShell><main className="mvp-page"><h1>Create listed option</h1><p role="alert">Currency catalogue unavailable. Reopen when the service is available.</p></main></WorkspaceShell>;}
  return <WorkspaceShell tenantName={workspace.tenantName} moduleCodes={workspace.moduleCodes} membershipRole={workspace.membershipRole}><main className="mvp-page"><h1>Create listed option</h1><p>Fixed-strike vanilla CALL/PUT, American/European, upfront premium. Submit the economic instrument for approval, then add its venue listing.</p><OptionForm currencies={currencies}/></main></WorkspaceShell>;
}
