import Link from "next/link";
import { Box, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import {
  CurrencyGroup,
  IndexFamilyOption,
  IndexKind,
  listCurrencies,
  listIndexFamilies,
  listIndexKinds,
  listOrganisations,
  listReturnProfiles,
  OrganisationOption,
  ReturnProfile,
} from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import NewIndexForm from "./form";

export const dynamic = "force-dynamic";

type CatalogueState = {
  currencies: CurrencyGroup[];
  returnProfiles: ReturnProfile[];
  organisations: OrganisationOption[];
  indexFamilies: IndexFamilyOption[];
  indexKinds: IndexKind[];
  error: string | null;
};

async function loadCatalogues(): Promise<CatalogueState> {
  let options;
  try { options = await requireReferenceTenantContext(); }
  catch { return {currencies:[],returnProfiles:[],organisations:[],indexFamilies:[],indexKinds:[],error:"Select an active tenant before loading reference catalogues."}; }
  const results = await Promise.allSettled([
    listCurrencies(options),
    listReturnProfiles(options),
    listOrganisations(options),
    listIndexFamilies(options),
    listIndexKinds(options),
  ]);
  const errors: string[] = [];
  const value = <T,>(index: number, label: string, fallback: T): T => {
    const result = results[index];
    if (result.status === "fulfilled") return result.value.data as T;
    errors.push(`${label}: ${result.reason instanceof Error ? result.reason.message : "unavailable"}`);
    return fallback;
  };
  return {
    currencies: value<CurrencyGroup[]>(0, "Currencies", []),
    returnProfiles: value<ReturnProfile[]>(1, "Return profiles", []),
    organisations: value<OrganisationOption[]>(2, "Organisations", []),
    indexFamilies: value<IndexFamilyOption[]>(3, "Index families", []),
    indexKinds: value<IndexKind[]>(4, "Index kinds", []),
    error: errors.length ? errors.join(" · ") : null,
  };
}

export default async function NewIndexPage() {
  const catalogues = await loadCatalogues();
  return (
    <WorkspaceShell>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
        <Box sx={{ maxWidth: 1080, mx: "auto" }}>
          <Typography variant="caption" color="text.secondary">
            <Link href="/">WORKSPACE / INSTRUMENTS</Link>
          </Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>Add an index</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>
            Create one concrete index variant. Price return, total return, net/gross return, and dividend-points variants are separate reference nodes linked to an optional index family.
          </Typography>
          <NewIndexForm {...catalogues} />
        </Box>
      </Box>
    </WorkspaceShell>
  );
}
