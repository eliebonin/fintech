import { WorkspacePageHeader } from "@/components/workspace-page-header";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import { redirect } from 'next/navigation';
import { WorkspaceShell } from '@/components/workspace-shell';
import { listCurrencies } from '@/lib/reference-api-client';
import OptionForm from './form';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function NewOptionPage() {
  let context,workspace;const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  let currencies;try{currencies=(await listCurrencies(context,['REGULAR'])).data;}catch{return <WorkspaceShell><main className="mvp-page"><WorkspacePageHeader title="Create listed option" eyebrow="INSTRUMENTS / OPTIONS" backHref="/instruments/create" backLabel="Back to instrument creation"/><p role="alert" className="error-panel">Currency catalogue unavailable. Reopen when the service is available.</p></main></WorkspaceShell>;}
  return <WorkspaceShell tenantName={workspace.tenantName} moduleCodes={workspace.moduleCodes} membershipRole={workspace.membershipRole}><main className="mvp-page"><WorkspacePageHeader title="Create listed option" eyebrow="INSTRUMENTS / OPTIONS" backHref="/instruments/create" backLabel="Back to instrument creation"><p>Fixed-strike vanilla CALL/PUT, American/European, upfront premium. Submit the economic instrument for approval, then add its venue listing.</p></WorkspacePageHeader><OptionForm currencies={currencies}/></main></WorkspaceShell>;
}
