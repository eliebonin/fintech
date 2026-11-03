import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {ReportingWorkspace} from '@/features/regulatory-reporting/workspace';
import './reporting.css';
export const dynamic='force-dynamic';
export default async function RegulatoryReportingPage(){
 const access=await resolveWorkspaceAccess();if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const w=access.workspace;const allowed=w.moduleCodes.includes('REGULATORY_REPORTING')&&w.permissionCodes?.includes('REPORTING_READ');
 return <WorkspaceShell tenantName={w.tenantName} membershipRole={w.membershipRole} moduleCodes={w.moduleCodes} permissionCodes={w.permissionCodes} userName={w.userName} actorId={w.actorId} sourceLabel="REGULATORY PREPARATION"><main className="mvp-page reg-page"><header className="mvp-header"><div><p className="eyebrow">REGULATORY REPORTING</p><h1>Transaction reporting</h1><p className="muted">Prepare, assess and review execution reports for a reporting legal entity.</p></div></header>{allowed?<ReportingWorkspace permissions={w.permissionCodes??[]}/>:<p role="alert">Regulatory Reporting must be enabled for this tenant, with reporting read access granted to your group.</p>}</main></WorkspaceShell>;
}
