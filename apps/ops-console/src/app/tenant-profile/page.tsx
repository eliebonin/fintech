import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {TenantProfileOverview} from '@/components/tenant-profile-overview';

export const dynamic='force-dynamic';

export default async function TenantProfilePage() {
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 return <WorkspaceShell {...access.workspace}><TenantProfileOverview workspace={access.workspace}/></WorkspaceShell>;
}
