import type { TradeBookingContext } from "@/lib/browser-api-client";
import { displayTradeProperty } from "@/lib/trade-property-display";
import type { TicketListing,TicketStrategy } from "./trade-ticket";
import {grossConsideration,type EnrichedTicketDraft} from "./ticket-model";
export function BookingReview({listing,draft,context,strategies}:{listing:TicketListing;draft:EnrichedTicketDraft;context:TradeBookingContext;strategies:TicketStrategy[]}) {
  const fields:[string,string][]=[
    ["Instrument",listing.canonicalName],["Listing",listing.tradingSymbol??listing.referenceNodeId],["Venue",listing.marketVenueMic??listing.venueName??"—"],["Currency",listing.tradingCurrency??"—"],
    ["Strategy",strategies.find(s=>s.strategyId===draft.strategyId)?.displayName??draft.strategyId],["Side",draft.side],["Quantity",draft.quantity],["Unit price",draft.executionPrice],["Trade time",draft.tradeDatetime],["Settlement date",draft.settlementDate],
    ["Counterparty",draft.counterpartyName||"Not specified"],["Executing broker",draft.executingBrokerName||"Not specified"],["Trader",draft.traderName||"Not specified"],["Booked by",context.bookedByUserAccountId],
    ["Trade type","INVESTMENT"],["Purpose",draft.tradePurpose],["Market activity",draft.marketActivity??"Not specified"],["Gross consideration",`${grossConsideration(draft.quantity,draft.executionPrice)} ${listing.tradingCurrency??""}`],
    ["Tags",context.tags.filter(t=>draft.tagIds.includes(t.tagId)).map(t=>t.label).join(", ")||"None"],
    ...context.properties.flatMap(def=>{const value=draft.properties[def.definitionId];return value===undefined||value===""?[]:[[def.label,displayTradeProperty(def.valueType,value,draft.propertyLabels?.[def.definitionId])] as [string,string]];}),
    ...draft.externalReferences.map(ref=>[`${ref.referenceType} (${ref.sourceSystemId||"unspecified source"})`,ref.referenceValue] as [string,string]),["Comment",draft.comment||"None"],
  ];
  return <section className="detail-card"><h2>Review booking</h2><p className="muted">Check all facts before confirming this immutable record of an already-executed trade. This does not send an order.</p><dl className="ticket-review">{fields.map(([label,value],index)=><div key={`${label}-${index}`}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><p className="muted">Settlement suggestion excludes weekends only; public holidays are not applied.</p></section>;
}
