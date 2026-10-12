import { WorkspacePageHeader } from "@/components/workspace-page-header";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {SwapCreationForm} from '@/components/swap-creation-form';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function NewSwapPage() {
  let context,workspace;const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page"><WorkspacePageHeader title="Create swap" eyebrow="INSTRUMENTS / SWAPS" backHref="/instruments/create" backLabel="Back to instrument creation"><p>Describe the sourced performance contract, review its terms, then submit a pending request for Operations approval.</p></WorkspacePageHeader><SwapCreationForm tenantId={context.tenantId}/></main></WorkspaceShell>;
}
