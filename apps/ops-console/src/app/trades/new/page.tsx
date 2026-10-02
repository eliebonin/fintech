import { notFound, redirect } from "next/navigation";

import { WorkspaceShell } from "@/components/workspace-shell";
import { searchReferenceNodes, getTradeBookingContext } from "@/lib/reference-api-client";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { TradeTicket, type TicketListing, type TicketStrategy } from "./trade-ticket";
import { FxForwardTicket } from "./fx-forward-ticket";
import { OptionTicket } from "./option-ticket";
import { ProductTicket } from './product-ticket';
import { isCashBookingListing } from '@/lib/cash-booking-listing';

export const dynamic = "force-dynamic";

export default async function NewTradePage({ searchParams }: { searchParams: Promise<{ listingId?: string;product?:string }> }) {
  const { listingId:requestedListingId, product } = await searchParams;
  const fx=product==="FX_FORWARD";
  const option=product==="OPTION";
  const extended=product==='STRUCTURED_PRODUCT'||product==='FUTURE'||product==='BOND';
  const listingId=fx||option||extended?undefined:requestedListingId;
  let context; let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  if (workspace.membershipRole !== "TENANT_ADMIN" || !workspace.moduleCodes.includes("TRADING")) redirect("/trades");
  let bookingContext;
  try { bookingContext = (await getTradeBookingContext(context)).data; }
  catch { return <WorkspaceShell sourceLabel="API UNAVAILABLE" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page"><h1>Book listed cash trade</h1><p className="error-panel" role="alert">Booking configuration could not be loaded. Reopen the page when the service is available; required properties cannot be safely omitted.</p></main></WorkspaceShell>; }
  const [nodes, strategiesResponse] = await Promise.all([
    listingId ? searchReferenceNodes(listingId, { ...context, referenceLevel: "LISTING", limit: 10 }) : Promise.resolve({ data: [] }),
    fetch(new URL("/v1/strategies", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), { headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId }, cache: "no-store" }),
  ]);
  const listing = listingId ? nodes.data.find((node) => node.referenceNodeId === listingId) : undefined;
  if (listingId && (!listing || !isCashBookingListing(listing))) notFound();
  const strategies = strategiesResponse.ok ? ((await strategiesResponse.json()) as { data: TicketStrategy[] }).data.filter((strategy) => strategy.status === "ACTIVE") : [];
  return <WorkspaceShell sourceLabel={strategiesResponse.ok ? "LIVE API" : "API UNAVAILABLE"} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><nav className="ticket-actions" aria-label="Booking product"><a href="/trades/new" aria-current={!fx&&!option&&!extended?"page":undefined}>Listed cash</a><a href="/trades/new?product=FX_FORWARD" aria-current={fx?"page":undefined}>Deliverable FX forward</a><a href="/trades/new?product=OPTION" aria-current={option?"page":undefined}>Listed option</a><a href="/trades/new?product=STRUCTURED_PRODUCT" aria-current={product==='STRUCTURED_PRODUCT'?'page':undefined}>Structured security</a><a href="/trades/new?product=FUTURE" aria-current={product==='FUTURE'?'page':undefined}>Future</a><a href="/trades/new?product=BOND" aria-current={product==='BOND'?'page':undefined}>Bond</a></nav>{extended?<ProductTicket key={`${context.tenantId}:${product}`} kind={product} strategies={strategies} context={bookingContext}/>:option?<OptionTicket key={context.tenantId} strategies={strategies} context={bookingContext}/>:fx?<FxForwardTicket key={context.tenantId} strategies={strategies} context={bookingContext}/>:<TradeTicket key={context.tenantId} listing={listing as TicketListing} strategies={strategies} context={bookingContext}/>}</WorkspaceShell>;
}
