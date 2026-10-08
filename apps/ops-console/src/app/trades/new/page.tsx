import { notFound, redirect } from "next/navigation";

import { WorkspaceShell } from "@/components/workspace-shell";
import { ReferenceApiError, getCashBookingListing, getTradeBookingContext } from "@/lib/reference-api-client";
import { getActiveTenantContext, getActiveTenantWorkspace } from "@/lib/tenant-session";
import { TradeTicket, type TicketListing, type TicketStrategy } from "./trade-ticket";
import { FxForwardTicket } from "./fx-forward-ticket";
import { OptionTicket } from "./option-ticket";
import { ProductTicket } from './product-ticket';
import {getBookedTradeDetail, MvpApiError} from '@/lib/mvp-api-client';
import {bookingCorrectionEligibility} from '@/lib/trade-correction-model';
import {CorrectionBookingGate} from '../record-correction-controls';
import type {TradeDetailPayload} from '@/lib/trades';
import {canBookTrades} from '@/lib/instrument-authority';

export const dynamic = "force-dynamic";

export default async function NewTradePage({ searchParams }: { searchParams: Promise<{ listingId?: string;product?:string;corrects?:string }> }) {
  const { listingId:requestedListingId, product:requestedProduct, corrects } = await searchParams;
  let context; let workspace;
  try { [context, workspace] = await Promise.all([getActiveTenantContext(), getActiveTenantWorkspace()]); } catch { redirect("/select-tenant"); }
  if (!canBookTrades(workspace)) return <WorkspaceShell moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}>{null}</WorkspaceShell>;
  let original:TradeDetailPayload['data']|undefined;
  if(corrects){
    if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(corrects))notFound();
    try {original=(await getBookedTradeDetail(context,corrects)).data;}
    catch(error){
      if(error instanceof MvpApiError&&error.status===404)notFound();
      return <WorkspaceShell sourceLabel="API UNAVAILABLE" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page"><h1>Replace booking</h1><p className="error-panel" role="alert">The original booking could not be loaded. No replacement ticket is available; reopen its detail when access and service are available.</p></main></WorkspaceShell>;
    }
    if(!bookingCorrectionEligibility(original).eligible)redirect(`/trades/${corrects}`);
  }
  const product=original?bookingCorrectionEligibility(original).product:requestedProduct;
  const fx=product==='FX_FORWARD',option=product==='OPTION';
  const extended=product==='STRUCTURED_PRODUCT'||product==='FUTURE'||product==='BOND'||product==='SWAP';
  const listingId=original||fx||option||extended?undefined:requestedListingId;
  let bookingContext;
  try { bookingContext = (await getTradeBookingContext(context)).data; }
  catch { return <WorkspaceShell sourceLabel="API UNAVAILABLE" moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page"><h1>Book listed cash trade</h1><p className="error-panel" role="alert">Booking configuration could not be loaded. Reopen the page when the service is available; required properties cannot be safely omitted.</p></main></WorkspaceShell>; }
  const [nodes, strategiesResponse] = await Promise.all([
    listingId ? getCashBookingListing(context,listingId).then(response=>({data:[response.data]})).catch(error=>{if(error instanceof ReferenceApiError&&error.status===404)notFound();throw error;}) : Promise.resolve({ data: [] }),
    fetch(new URL("/v1/strategies", process.env.REFERENCE_API_URL ?? "http://localhost:8000"), { headers: { "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId }, cache: "no-store" }),
  ]);
  const listing = listingId ? nodes.data.find((node) => node.referenceNodeId === listingId) : undefined;
  if (listingId && !listing) notFound();
  const strategies = strategiesResponse.ok ? ((await strategiesResponse.json()) as { data: TicketStrategy[] }).data.filter((strategy) => strategy.status === "ACTIVE"&&(!original||strategy.strategyId===original.trade.strategyId)) : [];
  const ticket=extended?<ProductTicket key={`${context.tenantId}:${product}`} kind={product} strategies={strategies} context={bookingContext}/>:option?<OptionTicket key={context.tenantId} strategies={strategies} context={bookingContext}/>:fx?<FxForwardTicket key={context.tenantId} strategies={strategies} context={bookingContext}/>:<TradeTicket key={context.tenantId} listing={listing?.bookingEligible?listing as TicketListing:undefined} strategies={strategies} context={bookingContext}/>;
  return <WorkspaceShell sourceLabel={strategiesResponse.ok ? "LIVE API" : "API UNAVAILABLE"} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}>
    {!original?<nav className="ticket-actions" aria-label="Booking product"><a href="/trades/new" aria-current={!fx&&!option&&!extended?"page":undefined}>Listed cash</a><a href="/trades/new?product=FX_FORWARD" aria-current={fx?"page":undefined}>Deliverable FX forward</a><a href="/trades/new?product=OPTION" aria-current={option?"page":undefined}>Listed option</a><a href="/trades/new?product=STRUCTURED_PRODUCT" aria-current={product==='STRUCTURED_PRODUCT'?'page':undefined}>Structured security</a><a href="/trades/new?product=FUTURE" aria-current={product==='FUTURE'?'page':undefined}>Future</a><a href="/trades/new?product=BOND" aria-current={product==='BOND'?'page':undefined}>Bond</a><a href="/trades/new?product=SWAP" aria-current={product==='SWAP'?'page':undefined}>Swap</a></nav>:null}
    <p className="muted">Historical execution dates use UTC. Current tenant permissions and governed annotations still apply. Only supported approved facts valid on execution can be used; retired or unavailable historical configuration is not reconstructed. Settlement dates are expected obligations, not payment confirmation.</p>
    {listing&&!listing.bookingEligible?<aside className="error-panel" role="alert"><p>{listing.ineligibilityMessage??"This listing is not ready to book."}</p><a href={`/instruments/${listing.parentReferenceNodeId}`}>Inspect instrument</a></aside>:null}
    {original?<CorrectionBookingGate key={`${context.tenantId}:${original.trade.tradeId}`} original={original} strategies={strategies} context={bookingContext}/>:ticket}
  </WorkspaceShell>;
}
