"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { createIdempotencyKey, searchReferenceNodesFromBff, submitBookedTradeFromBff, type TradeBookingRequest } from "@/lib/browser-api-client";

export type TicketListing = {
  referenceNodeId: string;
  canonicalName: string;
  marketVenueMic: string | null;
  venueName: string | null;
  tradingSymbol: string | null;
  tradingCurrency: string | null;
  status: string;
  isTradable: boolean;
};

export type TicketStrategy = { strategyId: string; strategyCode: string; displayName: string; status: string };

export type TicketDraft = {
  strategyId: string;
  side: "BUY" | "SELL";
  quantity: string;
  executionPrice: string;
  tradeDatetime: string;
  settlementDate: string;
  counterpartyOrganisationId?: string;
  externalReference?: string;
  comment?: string;
};

export function validateTicketDraft(draft: Omit<TicketDraft, "side">): string | null {
  if (!draft.strategyId) return "Select a strategy.";
  if (!Number.isFinite(Number(draft.quantity)) || Number(draft.quantity) <= 0) return "Quantity must be greater than zero.";
  if (!Number.isFinite(Number(draft.executionPrice)) || Number(draft.executionPrice) <= 0) return "Execution price must be greater than zero.";
  if (!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(draft.tradeDatetime) || Number.isNaN(Date.parse(draft.tradeDatetime))) return "Trade time must be an ISO 8601 timestamp with an offset.";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.settlementDate)) return "Settlement date is required.";
  if (draft.settlementDate < draft.tradeDatetime.slice(0, 10)) return "Settlement date cannot be before the trade date.";
  return null;
}

export function buildTicketPayload(listing: TicketListing, draft: TicketDraft): TradeBookingRequest {
  return {
    listingId: listing.referenceNodeId,
    strategyId: draft.strategyId,
    side: draft.side,
    quantity: draft.quantity,
    executionPrice: draft.executionPrice,
    tradeDatetime: draft.tradeDatetime,
    settlementDate: draft.settlementDate,
    ...(draft.counterpartyOrganisationId ? { counterpartyOrganisationId: draft.counterpartyOrganisationId } : {}),
    ...(draft.externalReference ? { externalReference: draft.externalReference } : {}),
    ...(draft.comment ? { comment: draft.comment } : {}),
  };
}

export function TradeTicket({ listing: initialListing, strategies }: { listing?: TicketListing; strategies: TicketStrategy[] }) {
  const router = useRouter();
  const retryKey = useRef(createIdempotencyKey());
  const [listing, setListing] = useState<TicketListing | undefined>(initialListing);
  const [listingQuery, setListingQuery] = useState("");
  const [listingResults, setListingResults] = useState<TicketListing[]>([]);
  const [searching, setSearching] = useState(false);
  const [draft, setDraft] = useState<TicketDraft>({ strategyId: "", side: "BUY", quantity: "", executionPrice: "", tradeDatetime: new Date().toISOString().replace(".000Z", "Z"), settlementDate: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const gross = useMemo(() => Number(draft.quantity) * Number(draft.executionPrice), [draft.quantity, draft.executionPrice]);
  const update = (field: keyof TicketDraft, value: string) => setDraft((current) => ({ ...current, [field]: value }));

  async function searchListings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!listingQuery.trim()) return;
    setSearching(true); setError("");
    try {
      const result = await searchReferenceNodesFromBff(listingQuery.trim(), { referenceLevel: "LISTING" });
      setListingResults(result.data.filter((candidate) => candidate.status === "ACTIVE" && candidate.isTradable) as TicketListing[]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Listings could not be searched.");
    } finally { setSearching(false); }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!listing) return;
    const validation = validateTicketDraft(draft);
    if (validation) { setError(validation); return; }
    setSaving(true); setError("");
    try {
      const result = await submitBookedTradeFromBff(buildTicketPayload(listing, draft), retryKey.current);
      router.push(`/trades/${encodeURIComponent(result.data.trade.tradeId)}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Trade could not be booked.");
      setSaving(false);
    }
  }

  if (!listing) return <main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">TRADE TICKET</p><h1>Book listed cash trade</h1><p className="muted">Search the active listing first. Its currency and venue will be locked before you enter the execution.</p></div><span className="synthetic-badge">STEP 1 OF 2</span></header>
    <form className="strategy-form" onSubmit={searchListings}><h2>Search active listings</h2><label>Listing, ticker, ISIN, or venue<input aria-label="Search active listings" value={listingQuery} onChange={(event) => setListingQuery(event.target.value)} placeholder="e.g. HSBC, XLON, ticker" required /></label><button type="submit" disabled={searching}>{searching ? "Searching…" : "Search listings"}</button>{error ? <p className="strategy-error">{error}</p> : null}</form>
    {listingResults.length ? <section className="table-wrap"><table><thead><tr><th>Instrument</th><th>Listing</th><th>Venue</th><th>Currency</th><th /></tr></thead><tbody>{listingResults.map((candidate) => <tr key={candidate.referenceNodeId}><td><strong>{candidate.canonicalName}</strong></td><td>{candidate.tradingSymbol ?? "—"}</td><td>{candidate.marketVenueMic ?? candidate.venueName ?? "—"}</td><td>{candidate.tradingCurrency ?? "—"}</td><td><button type="button" onClick={() => { setListing(candidate); setError(""); }}>Select listing</button></td></tr>)}</tbody></table></section> : null}
  </main>;

  return <main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">TRADE TICKET</p><h1>Book listed cash trade</h1><p className="muted">Record an already-executed BUY or SELL. Instrument, listing currency, and venue are derived from the active listing.</p></div><span className="synthetic-badge">LISTING-BOUND</span></header>
    <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">LOCKED EXECUTION SUBJECT</p><h2>{listing.canonicalName}</h2><p className="muted">{listing.tradingSymbol ?? "No symbol"} · {listing.marketVenueMic ?? "Venue unavailable"}</p></div></div><div className="detail-fields"><div className="detail-field"><small>Listing</small><strong>{listing.referenceNodeId}</strong></div><div className="detail-field"><small>Price currency</small><strong>{listing.tradingCurrency ?? "—"}</strong></div><div className="detail-field"><small>Execution venue</small><strong>{listing.venueName ?? listing.marketVenueMic ?? "—"}</strong></div></div></section>
    <form className="strategy-form" onSubmit={submit}><h2>Execution details</h2>
      <label>Strategy<select aria-label="Strategy" value={draft.strategyId} onChange={(event) => update("strategyId", event.target.value)} required><option value="">Select strategy</option>{strategies.map((strategy) => <option key={strategy.strategyId} value={strategy.strategyId}>{strategy.strategyCode} · {strategy.displayName}</option>)}</select></label>
      <label>Side<select aria-label="Side" value={draft.side} onChange={(event) => update("side", event.target.value)}><option value="BUY">BUY</option><option value="SELL">SELL</option></select></label>
      <label>Quantity<input aria-label="Quantity" inputMode="decimal" value={draft.quantity} onChange={(event) => update("quantity", event.target.value)} required /></label>
      <label>Execution price<input aria-label="Execution price" inputMode="decimal" value={draft.executionPrice} onChange={(event) => update("executionPrice", event.target.value)} required /></label>
      <label>Trade time (ISO 8601, offset required)<input aria-label="Trade time" value={draft.tradeDatetime} onChange={(event) => update("tradeDatetime", event.target.value)} required /></label>
      <label>Settlement date<input aria-label="Settlement date" type="date" value={draft.settlementDate} onChange={(event) => update("settlementDate", event.target.value)} required /></label>
      <label>External reference (optional)<input aria-label="External reference" value={draft.externalReference ?? ""} onChange={(event) => update("externalReference", event.target.value)} /></label>
      <label>Comment (optional)<input aria-label="Comment" value={draft.comment ?? ""} onChange={(event) => update("comment", event.target.value)} /></label>
      <p className="muted">Gross consideration: {Number.isFinite(gross) ? `${gross.toLocaleString("en-GB", { maximumFractionDigits: 4 })} ${listing.tradingCurrency ?? ""}` : "—"}</p>
      <button type="submit" disabled={saving || !listing.isTradable || listing.status !== "ACTIVE" || strategies.length === 0}>{saving ? "Booking…" : "Book trade"}</button><button type="button" onClick={() => { setListing(undefined); setListingResults([]); }}>Change listing</button>{error ? <p className="strategy-error">{error}</p> : null}
    </form>
  </main>;
}
