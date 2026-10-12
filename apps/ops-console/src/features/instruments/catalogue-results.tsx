import "server-only";
import { CatalogueWorkspace } from "./catalogue-workspace";
import { loadCatalogue } from "./catalogue-data";
import { ReferenceApiError } from "@/lib/reference-api-client";
import type { ActiveTenantWorkspace } from "@/lib/tenant-session";
import type { TenantContext } from "@/lib/tenant-types";
export async function CatalogueResults({ context, workspace }: { context: TenantContext; workspace: ActiveTenantWorkspace }) {
  try {
    const result = await loadCatalogue("", { ...context, status: "ACTIVE", limit: 25, offset: 0 });
    return <CatalogueWorkspace key={context.tenantId} workspace={workspace} initialResults={result.data} initialTotal={result.meta.total ?? result.data.length} initialSource={result.meta.source?.includes("fixture") ? "LOCAL FIXTURES" : "LIVE API"} />;
  } catch (error) {
    const forbidden = error instanceof ReferenceApiError && [401, 403].includes(error.status);
    return <CatalogueWorkspace key={context.tenantId} workspace={workspace} initialResults={[]} initialTotal={0} initialSource={forbidden ? "ACCESS RESTRICTED" : "API UNAVAILABLE"} initialError={forbidden ? "Your tenant access does not allow this catalogue. Ask your administrator to review your access." : "The instrument catalogue is temporarily unavailable. Try again."} />;
  }
}
