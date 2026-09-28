import Link from "next/link";
import { Box, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { listCurrencies, type CurrencyGroup } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import NewFxForwardForm from "./form";

export const dynamic = "force-dynamic";

type CatalogueState = {
  currencies: CurrencyGroup[];
  error: string | null;
};

async function loadCatalogues(): Promise<CatalogueState> {
  try {
    const result = await listCurrencies(resolveLocalTenantContext(), ["REGULAR"]);
    return { currencies: result.data, error: null };
  } catch (error) {
    return {
      currencies: [],
      error: error instanceof Error ? error.message : "Currency catalogue is unavailable",
    };
  }
}

export default async function NewFxForwardPage() {
  const catalogues = await loadCatalogues();
  return (
    <WorkspaceShell>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
        <Box sx={{ maxWidth: 1080, mx: "auto" }}>
          <Typography variant="caption" color="text.secondary">
            <Link href="/">WORKSPACE / INSTRUMENTS</Link>
          </Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>Add an FX forward</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>
            Create one OTC FX-forward economic contract. The base/quote convention and agreed rate are contractual terms; a counterparty MTM is recorded later as a valuation or market-data mark.
          </Typography>
          <NewFxForwardForm {...catalogues} />
        </Box>
      </Box>
    </WorkspaceShell>
  );
}
