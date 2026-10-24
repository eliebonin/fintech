import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspacePageHeader} from '@/components/workspace-page-header';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {AmcCreationForm} from '@/components/amc-creation-form';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {canManageInstruments} from '@/lib/instrument-authority';
export const dynamic='force-dynamic';
export default async function NewAmcPage(){
  const access=await resolveWorkspaceAccess();
  if(access.kind==='session-required')redirect('/select-context');
  if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
  const {workspace,context}=access;
  return <WorkspaceShell {...workspace}>{canManageInstruments(workspace)?<main className="mvp-page"><WorkspacePageHeader title="Create AMC" eyebrow="INSTRUMENTS / ACTIVELY MANAGED CERTIFICATES" backHref="/instruments/create" backLabel="Back to instrument creation"><p>Describe the certificate and its explicit booking terms. Submit it for approval before booking trades.</p></WorkspacePageHeader><AmcCreationForm tenantId={context.tenantId}/></main>:<main className="mvp-page"><h1>Create AMC</h1><p>Instrument-management permission is required. Ask your tenant administrator to review your access.</p></main>}</WorkspaceShell>;
}
