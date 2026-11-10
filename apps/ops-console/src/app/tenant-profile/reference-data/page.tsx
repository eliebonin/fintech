import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {ReferenceWorkspace} from '@/features/tenant-reference/reference-workspace';
export const dynamic='force-dynamic';
export default async function ReferencePage(){
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 return <WorkspaceShell {...workspace}>{workspace.permissionCodes?.includes('TRADE_CONFIGURE')?<ReferenceWorkspace key={workspace.tenantId+access.context.userAccountId} tenantId={workspace.tenantId}/>:<main className="mvp-page"><h1>Reference data</h1><p>Trade configuration permission is required to maintain tenant reference data.</p></main>}</WorkspaceShell>;
}
