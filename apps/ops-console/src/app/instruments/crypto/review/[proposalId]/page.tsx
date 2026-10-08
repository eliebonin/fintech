import Link from "next/link";
import { Alert, Box, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { getCryptoAssetProposal, ReferenceApiError } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import CryptoAssetProposalReviewForm from "./form";

export const dynamic = "force-dynamic";

export default async function CryptoAssetProposalReviewPage({ params }: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await params;

  try {
    const response = await getCryptoAssetProposal(proposalId, await requireReferenceTenantContext());
    return (
      <WorkspaceShell>
        <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
          <Box sx={{ maxWidth: 980, mx: "auto" }}>
            <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / OPERATIONS REVIEW</Link></Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>Review cryptoasset proposal</Typography>
            <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>
              Inspect the submitted economic identity before approving the canonical instrument and its currency role.
            </Typography>
            <CryptoAssetProposalReviewForm proposal={response.data} />
          </Box>
        </Box>
      </WorkspaceShell>
    );
  } catch (error) {
    const detail = error instanceof ReferenceApiError && error.status === 404
      ? "This cryptoasset proposal does not exist for the current tenant."
      : error instanceof Error ? error.message : "The cryptoasset proposal could not be loaded.";
    return (
      <WorkspaceShell>
        <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
          <Box sx={{ maxWidth: 980, mx: "auto" }}>
            <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / OPERATIONS REVIEW</Link></Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>Cryptoasset proposal unavailable</Typography>
            <Alert severity="error" sx={{ mt: 2 }}>{detail}</Alert>
            <Typography sx={{ mt: 2 }}><Link href="/">Return to the operations console</Link></Typography>
          </Box>
        </Box>
      </WorkspaceShell>
    );
  }
}
