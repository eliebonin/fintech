import Link from "next/link";
import { notFound } from "next/navigation";
import { Alert, Box, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { getReferenceDataProposal, ReferenceApiError } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import ReferenceDataProposalReviewForm from "./form";

export const dynamic = "force-dynamic";

export default async function ReferenceDataProposalReviewPage({ params }: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await params;

  try {
    const response = await getReferenceDataProposal(proposalId, await getActiveTenantContext());
    return (
      <WorkspaceShell>
        <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
          <Box sx={{ maxWidth: 1080, mx: "auto" }}>
            <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / OPERATIONS REVIEW</Link></Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>Review reference-data proposal</Typography>
            <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>
              Inspect the submitted payload and steward evidence before the owning workflow materialises canonical data.
            </Typography>
            <ReferenceDataProposalReviewForm proposal={response.data} />
          </Box>
        </Box>
      </WorkspaceShell>
    );
  } catch (error) {
    if (error instanceof ReferenceApiError && error.status === 404) notFound();
    const message = error instanceof Error ? error.message : "The reference-data proposal could not be loaded.";
    return (
      <WorkspaceShell sourceLabel="API UNAVAILABLE">
        <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
          <Box sx={{ maxWidth: 860, mx: "auto" }}>
            <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / OPERATIONS REVIEW</Link></Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>Proposal unavailable</Typography>
            <Alert severity="error" sx={{ mt: 2 }}>{message}</Alert>
            <Typography sx={{ mt: 2 }}><Link href="/">Return to the operations console</Link></Typography>
          </Box>
        </Box>
      </WorkspaceShell>
    );
  }
}
