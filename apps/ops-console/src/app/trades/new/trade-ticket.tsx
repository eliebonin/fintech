"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {withBookingCorrection,type BookingCorrection} from '@/lib/trade-correction-model';

import { createIdempotencyKey, searchCashBookingListingsFromBff, getCashBookingListingFromBff, submitBookedTradeFromBff, type CashBookingListingView, type TradeBookingRequest } from "@/lib/browser-api-client";
import type { TradeBookingContext } from "@/lib/browser-api-client";
import { BffApiError } from "@/lib/api-errors";
import { BookingSearchResults } from './booking-search-results';
import { PartyFields } from "./party-fields";
import { PropertyFields } from "./property-fields";
import { BookingReview } from "./booking-review";
import { buildEnrichedTicketPayload,validateEnrichedTicketDraft,revalidateEditedFields,editedTicketFields,grossConsideration,freezeBookingSubmission,bookingFailureMode,type EnrichedTicketDraft,type TicketError } from "./ticket-model";

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

// Alpha convenience default, not a venue-specific settlement rule: holidays
// are unavailable on the ticket. Use the UTC economic date, matching the API.
export function defaultSettlementDate(tradeDatetime: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(tradeDatetime) || Number.isNaN(Date.parse(tradeDatetime))) return "";
  const tradeDate = tradeDatetime.slice(0, 10);
  const enteredDate = new Date(`${tradeDate}T00:00:00Z`);
  if (Number.isNaN(enteredDate.getTime()) || enteredDate.toISOString().slice(0, 10) !== tradeDate) return "";
  const date = new Date(`${new Date(tradeDatetime).toISOString().slice(0,10)}T00:00:00Z`);
  for (let weekdays = 0; weekdays < 2;) {
    date.setUTCDate(date.getUTCDate() + 1);
    if (date.getUTCDay() !== 0 && date.getUTCDay() !== 6) weekdays += 1;
  }
  const result = date.toISOString().slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(result) ? result : "";
}

export function createTicketDraft(now: Date = new Date()): TicketDraft {
  const tradeDatetime = now.toISOString().replace(".000Z", "Z");
  return { strategyId: "", side: "BUY", quantity: "", executionPrice: "", tradeDatetime, settlementDate: defaultSettlementDate(tradeDatetime) };
}

export function updateTicketDraft(current: TicketDraft, field: keyof TicketDraft, value: string, settlementOverridden: boolean): TicketDraft {
  const next = { ...current, [field]: value };
  if (field === "tradeDatetime" && !settlementOverridden) {
    const suggested = defaultSettlementDate(value);
    if (suggested) next.settlementDate = suggested;
  }
  return next;
}

export function validateTicketDraft(draft: Omit<TicketDraft, "side">): string | null {
  return validateBasicTicketFields(draft)[0]?.message ?? null;
}

export function validateBasicTicketFields(draft: Omit<TicketDraft, "side">): TicketError[] {
  const errors: TicketError[] = [];
  if (!draft.strategyId) errors.push({field:"strategyId",message:"Select a strategy."});
  if (!Number.isFinite(Number(draft.quantity)) || Number(draft.quantity) <= 0) errors.push({field:"quantity",message:"Quantity must be greater than zero."});
  if (!Number.isFinite(Number(draft.executionPrice)) || Number(draft.executionPrice) <= 0) errors.push({field:"executionPrice",message:"Execution price must be greater than zero."});
  if (!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(draft.tradeDatetime) || Number.isNaN(Date.parse(draft.tradeDatetime))) errors.push({field:"tradeDatetime",message:"Trade time must be an ISO 8601 timestamp with an offset."});
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.settlementDate)) errors.push({field:"settlementDate",message:"Settlement date is required."});
  else if (!Number.isNaN(Date.parse(draft.tradeDatetime)) && draft.settlementDate < new Date(draft.tradeDatetime).toISOString().slice(0,10)) errors.push({field:"settlementDate",message:"Settlement date cannot be before the UTC trade date."});
  return errors;
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
    tradePurpose: "INVESTMENT",
    ...(draft.counterpartyOrganisationId ? { counterpartyOrganisationId: draft.counterpartyOrganisationId } : {}),
    ...(draft.externalReference ? { externalReference: draft.externalReference } : {}),
    ...(draft.comment ? { comment: draft.comment } : {}),
  };
}

export function TradeTicket({ listing: initialListing, strategies, correction, context = {tenantId:"",bookedByUserAccountId:"",properties:[],tags:[]} }: { listing?: TicketListing; strategies: TicketStrategy[]; context?:TradeBookingContext; correction?:BookingCorrection }) {
  const router = useRouter();
  const retryKey = useRef(createIdempotencyKey());
  const [listing, setListing] = useState<TicketListing | undefined>(initialListing);
  const [listingQuery, setListingQuery] = useState("");
  const [listingResults, setListingResults] = useState<CashBookingListingView[]>([]);
  const [searching, setSearching] = useState(false);
  const [draft, setDraft] = useState<EnrichedTicketDraft>(() => ({...createTicketDraft(),tradePurpose:"INVESTMENT",properties:{},tagIds:[],externalReferences:[]}));
  // Event handlers can run before React renders the last edit. Merge into the
  // latest draft, not the render closure, so unrelated values cannot be lost.
  const latestDraft=useRef(draft);
  const settlementOverridden = useRef(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const [reviewing,setReviewing]=useState(false);
  const [retryRequired,setRetryRequired]=useState(false);
  const [blocked,setBlocked]=useState(false);
  const [historyReviewed,setHistoryReviewed]=useState(false);
  const [fieldErrors,setFieldErrors]=useState<TicketError[]>([]);
  const submitted=useRef<{payload:TradeBookingRequest;key:string;expectedTenantId:string}|null>(null);
  const dirty=useRef(false);const errorSummary=useRef<HTMLDivElement>(null);
  useEffect(()=>{const warn=(event:BeforeUnloadEvent)=>{if(dirty.current){event.preventDefault();event.returnValue="";}};window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[]);
  useEffect(()=>{
    const ticketUrl=window.location.href;
    const ticketHistoryState=window.history.state;
    const backGuard=(event:PopStateEvent)=>{
      if(!dirty.current)return;
      const unresolved=inFlight.current||retryRequired||blocked;
      if(unresolved||!window.confirm("Discard the unbooked ticket?")){
        event.stopImmediatePropagation();
        window.history.pushState(ticketHistoryState,"",ticketUrl);
        if(unresolved)window.alert("Resolve this booking result before leaving. Retry an uncertain booking unchanged.");
      }else dirty.current=false;
    };
    const guard=(event:MouseEvent)=>{
      const link=(event.target as Element)?.closest?.("a[href]") as HTMLAnchorElement|null;
      if(!dirty.current||!link||link.target==="_blank"||link.hasAttribute("download")||link.getAttribute("href")?.startsWith("#"))return;
      if(inFlight.current||retryRequired||blocked){event.preventDefault();event.stopPropagation();window.alert("Resolve this booking result before leaving. An uncertain booking must be retried unchanged.");return;}
      if(!window.confirm("Discard the unbooked ticket?")){event.preventDefault();event.stopPropagation();}else dirty.current=false;
    };
    document.addEventListener("click",guard,true);
    window.addEventListener("popstate",backGuard,true);
    return()=>{document.removeEventListener("click",guard,true);window.removeEventListener("popstate",backGuard,true);};
  },[retryRequired,blocked]);
  const [errorFocusRequest,setErrorFocusRequest]=useState(0);
  useEffect(()=>{if(errorFocusRequest)errorSummary.current?.focus();},[errorFocusRequest]);
  const patch=(values:Partial<EnrichedTicketDraft>)=>{
    dirty.current=true;
    const currentDraft=latestDraft.current;
    const next={...currentDraft,...values};
    const edited=editedTicketFields(currentDraft,next,values);
    latestDraft.current=next;setDraft(next);
    setFieldErrors(current=>revalidateEditedFields(current,next,context,edited));
  };
  const update = (field: keyof TicketDraft, value: string) => {
    if (field === "settlementDate") settlementOverridden.current = true;
    const overridden = settlementOverridden.current;
    const next=updateTicketDraft(latestDraft.current, field, value, overridden);
    patch(field==="tradeDatetime"?{tradeDatetime:next.tradeDatetime,settlementDate:next.settlementDate}:{[field]:value});
  };

  const sequence=useRef(0);
  const [searched,setSearched]=useState(false),[total,setTotal]=useState(0);
  useEffect(()=>()=>{sequence.current++;},[]);
  function searchDate(){const value=new Date(latestDraft.current.tradeDatetime);return Number.isNaN(value.getTime())?'':value.toISOString().slice(0,10);}
  function invalidateSearch(){sequence.current++;setListingResults([]);setSearched(false);setSearching(false);setError('');}
  const nextOffset=useRef(0);
  async function searchListings(event: FormEvent,append=false) {
    event.preventDefault();
    if (!listingQuery.trim()) return;
    const serial=++sequence.current;
    setSearching(true); setError("");
    if(!append){setListingResults([]);setSearched(false);setTotal(0);}
    try {
      const result = await searchCashBookingListingsFromBff(listingQuery.trim(),searchDate(),append?nextOffset.current:0);
      if(serial===sequence.current){setListingResults(current=>append?[...current,...result.data]:result.data);setTotal(result.meta.total??result.data.length);nextOffset.current=(result.meta.offset??0)+(result.meta.limit??25);setSearched(true);}
    } catch (caught) {
      if(serial===sequence.current)setError(caught instanceof Error ? caught.message : "Listings could not be searched.");
    } finally { if(serial===sequence.current)setSearching(false); }
  }
  async function selectListing(id:string){
    const serial=++sequence.current;setSearching(true);setError('');
    try{
      const response=await getCashBookingListingFromBff(id,searchDate());
      if(serial!==sequence.current)return;
      if(!response.data.bookingEligible){
        setListingResults(current=>current.map(item=>item.referenceNodeId===id?response.data:item));
        throw new Error(response.data.ineligibilityMessage??'This listing is no longer ready. Inspect its configuration.');
      }
      setListing({...response.data,marketVenueMic:response.data.marketVenueMic??null,venueName:response.data.venueName??null,tradingSymbol:response.data.tradingSymbol??null,tradingCurrency:response.data.tradingCurrency??null});
    }catch(caught){if(serial===sequence.current)setError(caught instanceof Error?caught.message:'Readiness could not be checked.');}
    finally{if(serial===sequence.current)setSearching(false);}
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!listing) return;
    const validation = validateEnrichedTicketDraft(draft,context);
    setFieldErrors(validation);setError("");
    if(validation.length){setErrorFocusRequest(current=>current+1);return;}
    setReviewing(true);
  }

  async function confirmBooking() {
    if(!listing||inFlight.current||blocked)return;
    inFlight.current=true;
    if(!submitted.current)submitted.current=freezeBookingSubmission(withBookingCorrection(buildEnrichedTicketPayload(listing,draft,context),correction),retryKey.current,context.tenantId);
    setSaving(true); setError("");
    try {
      const result = await submitBookedTradeFromBff(submitted.current.payload,submitted.current.key,fetch,submitted.current.expectedTenantId);
      dirty.current=false;
      router.push(`/trades/${encodeURIComponent(result.data.trade.tradeId)}`);
    } catch (caught) {
      setErrorFocusRequest(current=>current+1);
      setError(caught instanceof Error ? caught.message : "Trade could not be booked.");
      if(caught instanceof BffApiError && caught.fieldErrors)setFieldErrors(Object.entries(caught.fieldErrors).flatMap(([field,messages])=>messages.map(message=>({field,message}))));
      const mode=bookingFailureMode(caught);
      const uncertain=mode==="RETRY_REQUIRED";
      setRetryRequired(uncertain);
      if(mode==="BLOCKED")setBlocked(true);
      if(mode==="EDITING"){submitted.current=null;setReviewing(false);}
      setSaving(false);
      inFlight.current=false;
    }
  }

  const errors = <div ref={errorSummary} tabIndex={-1} role={error||fieldErrors.length?"alert":undefined} className={error||fieldErrors.length?"strategy-error":""}>{error?<p>{error}</p>:null}{fieldErrors.length?<><h2>Check the following fields</h2><ul>{fieldErrors.map((issue,index)=><li key={index}><a href={`#${issue.field}`}>{issue.message}</a></li>)}</ul></>:null}</div>;
  function cancel(){if(!dirty.current||window.confirm("Discard the unbooked ticket?")){dirty.current=false;router.push("/trades");}}
  function leaveBlockedTicket(){
    if(!blocked||!historyReviewed)return;
    dirty.current=false;
    // A cross-tab tenant change can leave the client router's session stale.
    window.location.assign("/trades");
  }

  if (!listing) return <main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">TRADE TICKET</p><h1>Book listed cash trade</h1><p className="muted">Search the active listing first. Its currency and venue will be locked before you enter the execution.</p></div><span className="synthetic-badge">STEP 1 OF 2</span></header>
    <form className="strategy-form" onSubmit={e=>searchListings(e)}><h2>Search cash listings</h2><label>Listing, ticker, ISIN, or venue<input aria-label="Search active listings" value={listingQuery} maxLength={250} onChange={event=>{setListingQuery(event.target.value);invalidateSearch();}} placeholder="e.g. HSBC, XLON, ticker" required /></label><label>Readiness date (UTC execution date)<input type="date" aria-label="Cash readiness date" value={searchDate()} required onChange={e=>{if(e.target.value)update('tradeDatetime',e.target.value+'T'+latestDraft.current.tradeDatetime.slice(11));invalidateSearch();}}/></label><button type="submit" disabled={searching}>{searching ? "Searching…" : "Search listings"}</button>{error ? <p className="strategy-error" role="alert">{error}</p> : null}</form>
    <BookingSearchResults items={listingResults.map(candidate=>({id:candidate.referenceNodeId,instrumentId:candidate.parentReferenceNodeId??candidate.referenceNodeId,label:candidate.canonicalName,description:[candidate.tradingSymbol,candidate.venueName,candidate.tradingCurrency].filter(Boolean).join(' · '),bookingEligible:candidate.bookingEligible,readinessStatus:candidate.readinessStatus,ineligibilityMessage:candidate.ineligibilityMessage}))} loading={searching} searched={searched} total={total} hasMore={nextOffset.current<total} selectLabel="Select listing" loadMoreLabel="Load more listings" onSelect={id=>void selectListing(id)} onLoadMore={()=>void searchListings({preventDefault(){}} as FormEvent,true)}/>

  </main>;

  if(reviewing)return <main className="mvp-page"><h1>Review listed cash trade</h1>{errors}<BookingReview listing={listing} draft={draft} context={context} strategies={strategies}/><div className="ticket-actions"><button type="button" onClick={confirmBooking} disabled={saving||blocked}>{saving?"Booking…":retryRequired?"Retry unchanged booking":"Confirm booking"}</button><button type="button" disabled={saving||retryRequired||blocked} onClick={()=>setReviewing(false)}>Back to edit</button>{blocked?<><p role="alert">Booking is blocked. Check trade history before leaving this ticket. Resolve the tenant context or conflict before starting another booking.</p><a href="/trades" target="_blank" rel="noopener noreferrer">Check trade history in another tab</a><label><input type="checkbox" aria-label="I checked trade history and confirmed the booking result" checked={historyReviewed} onChange={event=>setHistoryReviewed(event.target.checked)}/>I checked trade history and confirmed the booking result.</label><button type="button" disabled={!historyReviewed} onClick={leaveBlockedTicket}>Leave blocked ticket</button></>:null}{retryRequired?<p role="status">The result is uncertain. Retry the unchanged request with its original key; do not book a second ticket.</p>:null}</div></main>;

  return <main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">TRADE TICKET</p><h1>Book listed cash trade</h1><p className="muted">Record an already-executed BUY or SELL. Instrument, listing currency, and venue are derived from the active listing.</p></div><span className="synthetic-badge">LISTING-BOUND</span></header>{errors}
    <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">LOCKED EXECUTION SUBJECT</p><h2>{listing.canonicalName}</h2><p className="muted">{listing.tradingSymbol ?? "No symbol"} · {listing.marketVenueMic ?? "Venue unavailable"}</p></div></div><div className="detail-fields"><div className="detail-field"><small>Listing</small><strong>{listing.referenceNodeId}</strong></div><div className="detail-field"><small>Price currency</small><strong>{listing.tradingCurrency ?? "—"}</strong></div><div className="detail-field"><small>Execution venue</small><strong>{listing.venueName ?? listing.marketVenueMic ?? "—"}</strong></div></div></section>
    <form className="strategy-form enriched-ticket" onSubmit={submit} noValidate><fieldset className="ticket-section"><legend>Execution details</legend>
      <label>Strategy<select aria-label="Strategy" id="strategyId" aria-invalid={fieldErrors.some(issue=>issue.field==="strategyId")} aria-describedby="strategyId-error" value={draft.strategyId} onChange={(event) => update("strategyId", event.target.value)} required><option value="">Select strategy</option>{strategies.map((strategy) => <option key={strategy.strategyId} value={strategy.strategyId}>{strategy.strategyCode} · {strategy.displayName}</option>)}</select><small id="strategyId-error">{fieldErrors.find(issue=>issue.field==="strategyId")?.message}</small></label>
      <label>Side<select aria-label="Side" value={draft.side} onChange={(event) => update("side", event.target.value)}><option value="BUY">BUY</option><option value="SELL">SELL</option></select></label>
      <label>Quantity<input aria-label="Quantity" id="quantity" aria-invalid={fieldErrors.some(issue=>issue.field==="quantity")} aria-describedby="quantity-error" inputMode="decimal" value={draft.quantity} onChange={(event) => update("quantity", event.target.value)} required /><small id="quantity-error">{fieldErrors.find(issue=>issue.field==="quantity")?.message}</small></label>
      <label>Execution price<input aria-label="Execution price" id="executionPrice" aria-invalid={fieldErrors.some(issue=>issue.field==="executionPrice")} aria-describedby="executionPrice-error" inputMode="decimal" value={draft.executionPrice} onChange={(event) => update("executionPrice", event.target.value)} required /><small id="executionPrice-error">{fieldErrors.find(issue=>issue.field==="executionPrice")?.message}</small></label>
      <label>Trade time (ISO 8601, offset required)<input aria-label="Trade time" id="tradeDatetime" aria-invalid={fieldErrors.some(issue=>issue.field==="tradeDatetime")} aria-describedby="tradeDatetime-error" value={draft.tradeDatetime} onChange={(event) => update("tradeDatetime", event.target.value)} required /><small id="tradeDatetime-error">{fieldErrors.find(issue=>issue.field==="tradeDatetime")?.message}</small></label>
      <label>Settlement date<input aria-label="Settlement date" type="date" id="settlementDate" aria-invalid={fieldErrors.some(issue=>issue.field==="settlementDate")} aria-describedby="settlement-default-hint settlementDate-error" value={draft.settlementDate} onChange={(event) => update("settlementDate", event.target.value)} required /><small id="settlement-default-hint">Defaults to T+2 weekdays (Mon–Fri). Holidays are not applied; review and adjust as needed.</small><small id="settlementDate-error">{fieldErrors.find(issue=>issue.field==="settlementDate")?.message}</small></label>
      <p className="muted">Gross consideration: {grossConsideration(draft.quantity,draft.executionPrice)} {listing.tradingCurrency??""}</p></fieldset>
      <PartyFields tenantId={context.tenantId} draft={draft} actor={context.bookedByUserAccountId} errors={fieldErrors} onChange={patch}/>
      <fieldset className="ticket-section"><legend>Trade classification</legend><p>Trade type: INVESTMENT</p><label>Purpose<select id="tradePurpose" value={draft.tradePurpose} onChange={e=>patch({tradePurpose:e.target.value as EnrichedTicketDraft["tradePurpose"]})}>{["INVESTMENT","REBALANCING","HEDGING","OTHER"].map(v=><option key={v}>{v}</option>)}</select></label><label>Market activity (optional)<select id="marketActivity" value={draft.marketActivity??""} onChange={e=>patch({marketActivity:(e.target.value||undefined) as EnrichedTicketDraft["marketActivity"]})}><option value="">Not specified</option><option>PRIMARY</option><option>SECONDARY</option></select></label></fieldset>
      <PropertyFields context={context} draft={draft} errors={fieldErrors} onChange={patch}/>
      <fieldset className="ticket-section"><legend>References and notes</legend>{draft.externalReferences.map((reference,index)=><div key={index} className="ticket-reference"><label>Reference type<select value={reference.referenceType} onChange={e=>patch({externalReferences:draft.externalReferences.map((r,i)=>i===index?{...r,referenceType:e.target.value as typeof r.referenceType}:r)})}><option>SOURCE_TRADE_ID</option><option>CLIENT_REFERENCE</option><option>BROKER_REFERENCE</option></select></label><label>Reference value<input id={`reference-${index}`} maxLength={500} value={reference.referenceValue} onChange={e=>patch({externalReferences:draft.externalReferences.map((r,i)=>i===index?{...r,referenceValue:e.target.value}:r)})}/></label><label>Source namespace (optional)<input maxLength={100} value={reference.sourceSystemId??""} onChange={e=>patch({externalReferences:draft.externalReferences.map((r,i)=>i===index?{...r,sourceSystemId:e.target.value}:r)})}/></label><button type="button" onClick={()=>patch({externalReferences:draft.externalReferences.filter((_,i)=>i!==index)})}>Remove reference</button></div>)}<button type="button" disabled={draft.externalReferences.length>=20} onClick={()=>patch({externalReferences:[...draft.externalReferences,{referenceType:"SOURCE_TRADE_ID",referenceValue:""}]})}>Add reference</button><label>Comment (optional unless purpose is OTHER)<textarea id="comment" aria-label="Comment" maxLength={10000} value={draft.comment??""} onChange={e=>patch({comment:e.target.value})}/></label></fieldset>
      <div className="ticket-actions"><button type="submit" disabled={!listing.isTradable || listing.status !== "ACTIVE" || strategies.length === 0}>Review booking</button><button type="button" onClick={()=>{setListing(undefined);invalidateSearch();setTotal(0);}}>Change listing</button><button type="button" onClick={cancel}>Cancel</button></div>
    </form>
  </main>;
}
