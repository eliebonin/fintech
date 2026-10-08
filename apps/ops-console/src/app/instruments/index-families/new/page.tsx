import Link from "next/link";
import { Box, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { listOrganisations, OrganisationOption } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import NewIndexFamilyForm from "./form";

export const dynamic = "force-dynamic";

type CatalogueState = {
  organisations: OrganisationOption[];
  error: string | null;
};

async function loadCatalogues(): Promise<CatalogueState> {
  try {
    const response = await listOrganisations(await requireReferenceTenantContext());
    return { organisations: response.data, error: null };
  } catch (error) {
    return {
      organisations: [],
      error: error instanceof Error ? error.message : "Organisation catalogue is unavailable",
    };
  }
}

export default async function NewIndexFamilyPage() {
  const catalogues = await loadCatalogues();
  return (
    <WorkspaceShell>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
        <Box sx={{ maxWidth: 920, mx: "auto" }}>
          <Typography variant="caption" color="text.secondary">
            <Link href="/">WORKSPACE / INSTRUMENTS</Link>
          </Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>Add an index family</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>
            Create the conceptual lineage first. Concrete price-return, total-return, net/gross, excess-return, or dividend-point variants are added afterwards as separate index records.
          </Typography>
          <NewIndexFamilyForm {...catalogues} />
        </Box>
      </Box>
    </WorkspaceShell>
  );
}
