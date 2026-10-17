import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {CashRegister} from '@/features/valuation/cash-register';
export const dynamic='force-dynamic';
export default async function CashBalancesPage(){
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access;
 const enabled=['MARKET_DATA','VALUATION'].every(code=>workspace.moduleCodes.includes(code))&&workspace.permissionCodes?.includes('VALUATION_READ');
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel="DATED CASH INPUTS"><main className="mvp-page pnl-page"><header><h1>Cash balances</h1><p><Link href="/valuation">Back to P&amp;L validation</Link></p></header>{enabled?<CashRegister canWrite={workspace.permissionCodes?.includes('VALUATION_RUN')??false}/>:<p role="alert">Valuation read access and the MARKET_DATA / VALUATION modules are required.</p>}</main></WorkspaceShell>;
}
