import { redirect } from "next/navigation";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import { CatalogueResults } from "@/features/instruments/catalogue-results";
export const dynamic = "force-dynamic";
export default async function InstrumentsPage() {
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  const { context, workspace } = access;
  // Let the router keep the current page visible until this page is ready.
  // Session/tenant validation still completes before any catalogue is returned.
  return CatalogueResults({ context, workspace });
}
