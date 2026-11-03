import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {InterestOpsReview} from './interest-ops-review';
import {BalanceExplorer} from './balance-explorer';
import {interestToday} from './interest-model';
export type InterestSearch=Promise<Record<string,string|string[]|undefined>>;
export async function InterestOpsPage({searchParams,stage}:{searchParams:InterestSearch;stage:'DAILY'|'BALANCE'|'EXPLORE'}){
 const access=await resolveWorkspaceAccess();if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access,params=await searchParams;
 const strategy=typeof params.strategyId==='string'&&/^[0-9a-f-]{36}$/i.test(params.strategyId)?params.strategyId:'';
 const rawDate=stage==='EXPLORE'?params.toDate:params.valueDate;
 const date=typeof rawDate==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(rawDate)?rawDate:interestToday();
 const start=new Date(`${date}T00:00:00Z`);if(Number.isNaN(start.getTime()))start.setTime(Date.now());start.setUTCDate(start.getUTCDate()-29);
 const from=typeof params.fromDate==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(params.fromDate)?params.fromDate:start.toISOString().slice(0,10);
 const instrument=typeof params.instrumentId==='string'&&/^[0-9a-f-]{36}$/i.test(params.instrumentId)?params.instrumentId:'';
 const enabled=['MARKET_DATA','VALUATION'].every(code=>workspace.moduleCodes.includes(code))&&workspace.permissionCodes?.includes('VALUATION_READ');
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel={stage==='EXPLORE'?'ACCRUED-BALANCE EXPLORER':'DAILY INTEREST OPERATIONS'}><main className="mvp-page pnl-page"><header className="pnl-page-heading"><div><h1>{stage==='EXPLORE'?'Explore accrued balances':stage==='DAILY'?'Daily accrual review':'Accrued-balance review'}</h1><p className="muted">{stage==='EXPLORE'?'Choose a strategy, instrument and date range to inspect stored balances, their chart and exact datapoints.':'Review one strategy and one day. Validate earned interest first, then the resulting local balances.'}</p></div></header>{enabled?stage==='EXPLORE'?<BalanceExplorer initialStrategy={strategy} initialInstrument={instrument} initialFrom={from} initialTo={date}/>:<InterestOpsReview stage={stage} initialStrategy={strategy} initialDate={date}/>:<p role="alert">Strategy valuation-read authority and MARKET_DATA / VALUATION modules are required.</p>}</main></WorkspaceShell>;
}
