import { WorkspacePageHeader } from "@/components/workspace-page-header";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import {redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {SwapCreationForm} from '@/components/swap-creation-form';
import {RateSwapCreationForm} from '@/components/rate-swap-creation-form';
import Link from 'next/link';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function NewSwapPage({searchParams}:{searchParams?:Promise<Record<string,string|string[]|undefined>>}={}) {
  const rate=(await searchParams)?.kind==='RATE_EXCHANGE';
  let context,workspace;const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId}>{null}</WorkspaceShell>;
  return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId}><main className="mvp-page"><WorkspacePageHeader title="Create swap" eyebrow="INSTRUMENTS / SWAPS" backHref="/instruments/create" backLabel="Back to instrument creation"><p>Choose the contract structure, review its sourced terms, then submit a pending request for Operations approval. Each two-leg component keeps its own instrument and bank price series.</p></WorkspacePageHeader><nav className="workspace-tabs workspace-route-tabs" aria-label="Swap structure"><Link href="/instruments/swaps/new" aria-current={!rate?'page':undefined}>Performance swap</Link><Link href="/instruments/swaps/new?kind=RATE_EXCHANGE" aria-current={rate?'page':undefined}>Rate versus rate</Link></nav>{rate?<RateSwapCreationForm tenantId={context.tenantId}/>:<SwapCreationForm tenantId={context.tenantId}/>}</main></WorkspaceShell>;
}
