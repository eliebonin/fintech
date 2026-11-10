import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {ReferenceCatalogue} from '@/features/tenant-reference/reference-catalogue';
export const dynamic='force-dynamic';
export default async function ReferencePage({params}:{params:Promise<{catalogueId:string}>}){
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 return <WorkspaceShell {...workspace}>{workspace.permissionCodes?.includes('TRADE_CONFIGURE')?<ReferenceCatalogue key={workspace.tenantId+access.context.userAccountId} tenantId={workspace.tenantId} catalogueId={(await params).catalogueId}/>:<main className="mvp-page"><h1>Reference data</h1><p>Trade configuration permission is required to maintain tenant reference data.</p></main>}</WorkspaceShell>;
}
