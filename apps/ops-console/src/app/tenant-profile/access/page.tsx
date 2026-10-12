import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {TenantAccessConsole} from '@/components/tenant-access-console';
export const dynamic='force-dynamic';
export default async function Page({searchParams}:{searchParams:Promise<{view?:string}>}){
 const {view}=await searchParams;
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 return <WorkspaceShell {...workspace}>{workspace.permissionCodes?.includes('ACCESS_MANAGE')?<TenantAccessConsole initialTab={view==='groups'?'groups':'users'}/>:<main className="mvp-page"><h1>Users &amp; groups</h1><p role="alert">Tenant administrator access is required.</p></main>}</WorkspaceShell>;
}
