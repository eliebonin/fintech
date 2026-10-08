import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {FutureExpiryForm} from '@/components/future-expiry-form';
import {getActiveTenantContext,getActiveTenantWorkspace} from '@/lib/tenant-session';
import {searchFutureFamilies} from '@/lib/reference-api-client';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function NewFuturePage({searchParams}:{searchParams:Promise<{familyCode?:string}>}){
  let context,workspace;try{[context,workspace]=await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]);}catch{redirect('/select-tenant');}
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  const shell={tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try{const code=(await searchParams).familyCode;const initialFamily=code?(await searchFutureFamilies(context,new URLSearchParams({q:code,limit:'100'}))).data.find(f=>f.familyCode===code):undefined;return <WorkspaceShell {...shell}><main className="mvp-page"><h1>Create future</h1><p>Family → canonical expiry → venue listing. Select approved family rules, enter the exact expiry dates, then review before submitting.</p><FutureExpiryForm tenantId={context.tenantId} initialFamily={initialFamily}/></main></WorkspaceShell>;}catch{return <WorkspaceShell {...shell}><main className="mvp-page"><h1>Create future</h1><p role="alert">Approved family catalogue unavailable. Try again when the service is available.</p></main></WorkspaceShell>;}
}
