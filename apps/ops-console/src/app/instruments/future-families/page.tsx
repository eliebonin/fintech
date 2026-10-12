import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {FutureFamilyForm} from '@/components/future-family-form';
import {listCurrencies} from '@/lib/reference-api-client';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function FamiliesPage({searchParams}:{searchParams:Promise<{view?:string}>}){
  let context,workspace;const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  const shell={tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try{const currencies=(await listCurrencies(context,['REGULAR','CRYPTO'])).data;return <WorkspaceShell {...shell}><main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">FAMILY → EXPIRY → LISTING</p><h1>Futures families</h1><p className="muted">Define the reusable product specification first. Individual expiries and venue listings follow approval.</p></div></header><FutureFamilyForm tenantId={context.tenantId} currencies={currencies} browse={(await searchParams).view==='browse'}/></main></WorkspaceShell>;}catch{return <WorkspaceShell {...shell}><main className="mvp-page"><h1>Futures families</h1><p role="alert">Currency catalogue unavailable. Try again later.</p></main></WorkspaceShell>;}
}
