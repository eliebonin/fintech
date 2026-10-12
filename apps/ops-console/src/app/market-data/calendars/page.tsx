import {MarketDataNavigation} from '@/components/market-data-navigation';
import Link from 'next/link';
import {redirect} from 'next/navigation';
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";

import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {WorkspaceShell} from '@/components/workspace-shell';
import {CalendarConsole} from '@/components/calendar-console';
export const dynamic='force-dynamic';
export default async function CalendarsPage() {
 const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;

 const {workspace}=access; const enabled=workspace.moduleCodes.includes('MARKET_DATA');
 let options=null;
 try{if(enabled)options=(await (await pricingPolicyClient()).GET('/v1/market-data/calendars/options')).data;}catch{/* Never use another tenant's fallback. */}
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page">{enabled?<MarketDataNavigation active="calendars"/>:null}<header className="mvp-header"><div><p className="eyebrow">GOVERNED BUSINESS DATES</p><h1>Fund and strategy calendars</h1><p>Versioned tenant schedules, reference calendars and documented date exceptions.</p><Link href="/market-data">Back to Market data</Link></div></header>{!enabled?<p className="error-panel">MARKET_DATA is not enabled.</p>:options?<CalendarConsole options={options}/>:<p className="error-panel">Calendar service is unavailable. No default calendar is assumed.</p>}</main></WorkspaceShell>;
}
