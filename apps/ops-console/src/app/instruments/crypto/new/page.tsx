import Link from "next/link";
import { Box, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { listOrganisations, OrganisationOption } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import NewCryptoAssetForm from "./form";

export const dynamic = "force-dynamic";

type CatalogueState = {
  organisations: OrganisationOption[];
  error: string | null;
};

async function loadCatalogues(): Promise<CatalogueState> {
  try {
    const response = await listOrganisations(resolveLocalTenantContext());
    return { organisations: response.data, error: null };
  } catch (error) {
    return {
      organisations: [],
      error: error instanceof Error ? error.message : "Organisation catalogue is unavailable",
    };
  }
}

export default async function NewCryptoAssetPage() {
  const catalogues = await loadCatalogues();
  return (
    <WorkspaceShell>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
        <Box sx={{ maxWidth: 980, mx: "auto" }}>
          <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS</Link></Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>Add a cryptoasset</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>
            Create the canonical economic asset first. Chain deployments and venue listings are separate records because one cryptoasset can exist on several networks and trade in many currency pairs.
          </Typography>
          <NewCryptoAssetForm {...catalogues} />
        </Box>
      </Box>
    </WorkspaceShell>
  );
}
