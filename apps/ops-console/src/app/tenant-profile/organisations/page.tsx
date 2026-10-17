import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {OrganisationConsole} from '@/features/organisations/organisation-console';
import './organisations.css';

export const dynamic='force-dynamic';
export default async function OrganisationPage(){
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 return <WorkspaceShell {...workspace}>{workspace.permissionCodes?.includes('TRADE_CONFIGURE')
  ?<OrganisationConsole key={workspace.tenantId} tenantId={workspace.tenantId}/>
  :<main className="mvp-page"><h1>Organisations</h1><p>Trade configuration permission in the Trading module is required. Ask your tenant administrator to review your groups.</p></main>}</WorkspaceShell>;
}
