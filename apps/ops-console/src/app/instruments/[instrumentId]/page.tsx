import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { Alert, Box, Typography } from "@mui/material";

import { InstrumentDetail } from "@/components/instrument-detail";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getInstrument, MvpApiError } from "@/lib/mvp-api-client";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { getInstrument as getFixtureInstrument } from "@/lib/instrument-data";
import {getProductInstrument} from '@/lib/reference-api-client';

export const dynamic = "force-dynamic";

export default async function InstrumentPage({ params }: { params: Promise<{ instrumentId: string }> }) {
  const { instrumentId } = await params;
  let context, workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]); }
  catch { redirect('/select-tenant'); }
  const shell = {tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try {
    const response = await getInstrument(context, instrumentId);
    const futureTerms=response.data.instrumentType==='FUTURE' ? await getProductInstrument(context,instrumentId,new URLSearchParams()).then(r=>r.data).catch(()=>undefined) : undefined;
    return <WorkspaceShell {...shell} sourceLabel="LIVE API"><InstrumentDetail instrument={response.data} futureTerms={futureTerms} standalone /></WorkspaceShell>;
  } catch (error) {
    if (error instanceof MvpApiError && error.status === 404) notFound();

    const allowFixtureFallback = process.env.NODE_ENV !== "production" && process.env.ALLOW_FIXTURE_FALLBACK === "true";
    const fixture = allowFixtureFallback ? getFixtureInstrument(instrumentId) : undefined;
    if (fixture) {
      return <WorkspaceShell {...shell} sourceLabel="LOCAL FIXTURE"><InstrumentDetail instrument={fixture} standalone /></WorkspaceShell>;
    }

    const message = error instanceof MvpApiError && error.status === 403
      ? "You are not authorised to view this canonical instrument."
      : error instanceof Error
        ? error.message
        : "The canonical instrument could not be loaded.";
    return (
      <WorkspaceShell {...shell} sourceLabel="API UNAVAILABLE">
        <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
          <Box sx={{ maxWidth: 860, mx: "auto" }}>
            <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS</Link></Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>Instrument detail unavailable</Typography>
            <Alert severity={error instanceof MvpApiError && error.status === 403 ? "warning" : "error"} sx={{ mt: 2 }}>{message}</Alert>
            <Typography sx={{ mt: 2 }}><Link href="/">Return to the operations console</Link></Typography>
          </Box>
        </Box>
      </WorkspaceShell>
    );
  }
}
