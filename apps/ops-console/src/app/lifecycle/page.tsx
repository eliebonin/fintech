import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {LifecycleWorklist} from '@/features/lifecycle-worklist/worklist-console';
export const dynamic='force-dynamic';
export default async function LifecycleWorklistPage({searchParams}:{searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const access=await resolveWorkspaceAccess();if(access.kind==='session-required')redirect('/select-context');if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace,context}=access,query=await searchParams,initial:Record<string,string>={};
 for(const key of ['fromDate','toDate','strategyId','q','attention','status','includeEarlierOverdue'])if(typeof query[key]==='string')initial[key]=query[key];
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel="LIFECYCLE WORKLIST"><main className="mvp-page">{workspace.permissionCodes?.includes('LIFECYCLE_READ')?<LifecycleWorklist key={context.tenantId+context.userAccountId} tenantId={context.tenantId} actorId={context.userAccountId} initial={initial}/>:<><h1>Lifecycle events</h1><p>Explicit strategy-scoped lifecycle read permission is required. <Link href="/tenant-profile/access?view=groups">Review group access</Link>.</p></>}</main></WorkspaceShell>;
}
