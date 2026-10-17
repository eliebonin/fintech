import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {EffectiveAccessConsole} from '@/components/effective-access';
export const dynamic='force-dynamic';
export default async function Page({searchParams}:{searchParams:Promise<{userId?:string}>}) {
 const {userId}=await searchParams;
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 return <WorkspaceShell {...workspace}><EffectiveAccessConsole key={`${workspace.tenantId}:${access.context.userAccountId}:${userId??'self'}`} userId={userId}/></WorkspaceShell>;
}
