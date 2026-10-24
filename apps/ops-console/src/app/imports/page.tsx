import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {canBookTrades} from '@/lib/instrument-authority';
import {ImportConsole} from '@/features/imports/import-console';

export const dynamic='force-dynamic';
export default async function ImportsPage(){
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 return <WorkspaceShell {...workspace}><ImportConsole key={`${workspace.tenantId}:${workspace.actorId}`} tenantId={workspace.tenantId} canWrite={canBookTrades(workspace)}/></WorkspaceShell>;
}
