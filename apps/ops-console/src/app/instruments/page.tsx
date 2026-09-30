export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";

import { InstrumentCatalogue } from "@/components/instrument-catalogue";
import { WorkspaceShell } from "@/components/workspace-shell";
import { searchInstruments } from "@/lib/instrument-data";
import { searchReferenceInstruments } from "@/lib/reference-api-client";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";

export default async function InstrumentsPage() {
  let initialResults = searchInstruments("");
  let initialSource = "synthetic-fixture";
  let tenantContext;
  let workspace;
  try { [tenantContext, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  try {
    const response = await searchReferenceInstruments("", tenantContext);
    initialResults = response.data;
    initialSource = response.meta.source;
  } catch { /* Local fixtures retain an inspectable catalogue when the API is down. */ }
  return <WorkspaceShell sourceLabel={initialSource === "live-reference-api" ? "LIVE API" : "LOCAL FIXTURES"} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><InstrumentCatalogue initialResults={initialResults} /></WorkspaceShell>;
}
