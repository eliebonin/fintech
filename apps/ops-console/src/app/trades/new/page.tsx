import { notFound, redirect } from "next/navigation";

import { WorkspaceShell } from "@/components/workspace-shell";
import { searchReferenceNodes } from "@/lib/reference-api-client";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { TradeTicket, type TicketListing, type TicketStrategy } from "./trade-ticket";

export const dynamic = "force-dynamic";

export default async function NewTradePage({ searchParams }: { searchParams: Promise<{ listingId?: string }> }) {
  const { listingId } = await searchParams;
  let context; let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  if (workspace.membershipRole !== "TENANT_ADMIN" || !workspace.moduleCodes.includes("TRADING")) redirect("/trades");
  const [nodes, strategiesResponse] = await Promise.all([
    listingId ? searchReferenceNodes(listingId, { ...context, referenceLevel: "LISTING", limit: 10 }) : Promise.resolve({ data: [] }),
    fetch(new URL("/v1/strategies", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), { headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId }, cache: "no-store" }),
  ]);
  const listing = listingId ? nodes.data.find((node) => node.referenceNodeId === listingId) : undefined;
  if (listingId && (!listing || listing.status !== "ACTIVE" || !listing.isTradable)) notFound();
  const strategies = strategiesResponse.ok ? ((await strategiesResponse.json()) as { data: TicketStrategy[] }).data.filter((strategy) => strategy.status === "ACTIVE") : [];
  return <WorkspaceShell sourceLabel={strategiesResponse.ok ? "LIVE API" : "API UNAVAILABLE"} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><TradeTicket listing={listing as TicketListing} strategies={strategies} /></WorkspaceShell>;
}
