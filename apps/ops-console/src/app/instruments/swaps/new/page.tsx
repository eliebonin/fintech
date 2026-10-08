import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {SwapCreationForm} from '@/components/swap-creation-form';
import {getActiveTenantContext,getActiveTenantWorkspace} from '@/lib/tenant-session';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function NewSwapPage() {
  let context,workspace;try{[context,workspace]=await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]);}catch{redirect('/select-tenant');}
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page"><h1>Create swap</h1><p>Describe the sourced performance contract, review its terms, then submit a pending request for Operations approval.</p><SwapCreationForm tenantId={context.tenantId}/></main></WorkspaceShell>;
}
