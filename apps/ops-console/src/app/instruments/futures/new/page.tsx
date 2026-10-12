import { WorkspacePageHeader } from "@/components/workspace-page-header";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {FutureExpiryForm} from '@/components/future-expiry-form';
import {searchFutureFamilies} from '@/lib/reference-api-client';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function NewFuturePage({searchParams}:{searchParams:Promise<{familyCode?:string}>}){
  let context,workspace;const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  const shell={tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try{const code=(await searchParams).familyCode;const initialFamily=code?(await searchFutureFamilies(context,new URLSearchParams({q:code,limit:'100'}))).data.find(f=>f.familyCode===code):undefined;return <WorkspaceShell {...shell}><main className="mvp-page"><WorkspacePageHeader title="Create future" eyebrow="INSTRUMENTS / FUTURES" backHref="/instruments/create" backLabel="Back to instrument creation"><p>Family → canonical expiry → venue listing. Select approved family rules, enter the exact expiry dates, then review before submitting.</p></WorkspacePageHeader><FutureExpiryForm tenantId={context.tenantId} initialFamily={initialFamily}/></main></WorkspaceShell>;}catch{return <WorkspaceShell {...shell}><main className="mvp-page"><WorkspacePageHeader title="Create future" eyebrow="INSTRUMENTS / FUTURES" backHref="/instruments/create" backLabel="Back to instrument creation"/><p role="alert" className="error-panel">Approved family catalogue unavailable. Try again when the service is available.</p></main></WorkspaceShell>;}
}
