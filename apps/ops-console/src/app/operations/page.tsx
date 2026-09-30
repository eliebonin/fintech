export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";
import { Alert, Box, Typography } from "@mui/material";

import { OperationsWorkQueue } from "@/components/operations-work-queue";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { getWorkQueue } from "@/lib/work-queue";

export default async function OperationsPage() {
  let tenantContext;
  let workspace;
  try { [tenantContext, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }

  try {
    const queue = await getWorkQueue(tenantContext);
    return <WorkspaceShell sourceLabel="LIVE API" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><Box sx={{ px: { xs: 2, md: 3.5 }, py: 3, maxWidth: 1180 }}><Typography variant="overline" color="text.secondary">OPERATIONS / REVIEW QUEUE</Typography><Typography variant="h5">Operations</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>A tenant-scoped inbox for pending reference-data, mapping, NAV, and market-data decisions. Instrument requests remain in the Instruments workspace.</Typography><OperationsWorkQueue queue={queue} /></Box></WorkspaceShell>;
  } catch {
    return <WorkspaceShell sourceLabel="API UNAVAILABLE" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><Box sx={{ px: { xs: 2, md: 3.5 }, py: 3, maxWidth: 1180 }}><Typography variant="overline" color="text.secondary">OPERATIONS / REVIEW QUEUE</Typography><Typography variant="h5" sx={{ mb: 2 }}>Operations</Typography><Alert severity="warning">The operations queue is temporarily unavailable. No fixture or unrelated data has been substituted.</Alert></Box></WorkspaceShell>;
  }
}
