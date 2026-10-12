import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";
import { Alert, Box, Typography } from "@mui/material";

import { OperationsWorkQueue } from "@/components/operations-work-queue";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getWorkQueue } from "@/lib/work-queue";
import {QueuePagination,queueOffset} from '@/components/queue-pagination';

export default async function OperationsPage({searchParams}:{searchParams?:Promise<{offset?:string}>}={}) {
  let tenantContext;
  let workspace;
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  tenantContext = access.context; workspace = access.workspace;

  try {
    const offset=queueOffset((await searchParams)?.offset);
    const queue = await getWorkQueue({...tenantContext,offset});
    return <WorkspaceShell sourceLabel="LIVE API" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><Box sx={{ px: { xs: 2, md: 3.5 }, py: 3, maxWidth: 1180 }}><Typography variant="overline" color="text.secondary">OPERATIONS / REVIEW QUEUE</Typography><Typography variant="h5">Operations</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>A tenant-scoped inbox for pending reference-data, mapping, NAV, and market-data decisions. Instrument requests remain in the Instruments workspace.</Typography><QueuePagination meta={queue.meta} path="/operations" /><OperationsWorkQueue queue={queue} /><QueuePagination meta={queue.meta} path="/operations" /></Box></WorkspaceShell>;
  } catch {
    return <WorkspaceShell sourceLabel="API UNAVAILABLE" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><Box sx={{ px: { xs: 2, md: 3.5 }, py: 3, maxWidth: 1180 }}><Typography variant="overline" color="text.secondary">OPERATIONS / REVIEW QUEUE</Typography><Typography variant="h5" sx={{ mb: 2 }}>Operations</Typography><Alert severity="warning">The operations queue is temporarily unavailable. No fixture or unrelated data has been substituted.</Alert></Box></WorkspaceShell>;
  }
}
