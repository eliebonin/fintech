export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";

import { InstrumentCatalogue } from "@/components/instrument-catalogue";
import { WorkspaceShell } from "@/components/workspace-shell";
import { searchInstruments } from "@/lib/instrument-data";
import { searchReferenceInstruments } from "@/lib/reference-api-client";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import {canManageInstruments} from '@/lib/instrument-authority';

export default async function InstrumentsPage() {
  let initialResults = searchInstruments("");
  let initialSource = "synthetic-fixture";
  let initialTotal = initialResults.length;
  let tenantContext;
  let workspace;
  try { [tenantContext, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  try {
    const response = await searchReferenceInstruments("", { ...tenantContext, status: "ACTIVE", limit: 25, offset: 0 });
    initialResults = response.data;
    initialSource = response.meta.source;
    initialTotal = response.meta.total ?? response.data.length;
  } catch { /* Local fixtures retain an inspectable catalogue when the API is down. */ }
  return <WorkspaceShell sourceLabel={initialSource === "live-reference-api" ? "LIVE API" : "LOCAL FIXTURES"} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><InstrumentCatalogue initialResults={initialResults} initialTotal={initialTotal} canManage={canManageInstruments(workspace)} /></WorkspaceShell>;
}
