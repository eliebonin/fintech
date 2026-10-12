"use client";
import { useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { InstrumentCatalogue } from "@/components/instrument-catalogue";
import type { ActiveTenantWorkspace } from "@/lib/tenant-session";
import type { InstrumentCatalogueItem } from "api-contracts";
import { canManageInstruments } from "@/lib/instrument-authority";
export function CatalogueWorkspace({ workspace, initialResults, initialTotal, initialSource, initialError = "" }: {
  workspace: ActiveTenantWorkspace; initialResults: InstrumentCatalogueItem[]; initialTotal: number; initialSource: string; initialError?: string;
}) {
  const [source, setSource] = useState(initialSource);
  return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} sourceLabel={source}>
    <InstrumentCatalogue initialResults={initialResults} initialTotal={initialTotal} initialError={initialError} canManage={canManageInstruments(workspace)} onSourceChange={setSource} />
  </WorkspaceShell>;
}
