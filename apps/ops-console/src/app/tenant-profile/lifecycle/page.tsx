import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {LifecycleDowngradeWorkspace} from '@/features/lifecycle-assistance/downgrade-workspace';
export const dynamic='force-dynamic';
export default async function LifecycleSettingsPage(){
 const access=await resolveWorkspaceAccess();if(access.kind==='session-required')redirect('/select-context');if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const workspace=access.workspace;
 return <WorkspaceShell {...workspace}>{workspace.permissionCodes?.includes('LIFECYCLE_READ')?<LifecycleDowngradeWorkspace key={workspace.tenantId+access.context.userAccountId} tenantId={workspace.tenantId}/>:<main className="mvp-page"><h1>Lifecycle assistance settings</h1><p>Explicit lifecycle read and configuration permissions are required. Tenant administrator status alone does not grant them.</p></main>}</WorkspaceShell>;
}
