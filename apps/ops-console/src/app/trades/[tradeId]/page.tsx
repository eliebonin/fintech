import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import Link from "next/link";
import {productAmount} from "@/app/trades/new/product-ticket-model";
import { redirect } from "next/navigation";

import { describeMvpError, getBookedTradeDetail, MvpApiError } from "@/lib/mvp-api-client";
import { displayTradeProperty } from "@/lib/trade-property-display";
import { formatTradeDateTime, formatTradeNumber, formatTradeExactDecimal, tradeDirection, type TradeDetailPayload } from "@/lib/trades";
import { WorkspaceShell } from "@/components/workspace-shell";
import {SwapTermsFacts} from "@/components/swap-terms-facts";
import { bookedSwapFacts, safeHistoryReturn, type HistorySearchParams } from "@/lib/trade-history";
import {bookingCorrectionLinks} from "@/lib/trade-correction-model";
import {RecordCorrectionActions} from "../record-correction-controls";
import {FxDeliveryControls,DeliveryEventFacts,type FxDeliveryProgress} from '../fx-delivery-controls';
import {getFxDelivery} from '@/lib/reference-api-client';

export const dynamic = "force-dynamic";

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return <div className="detail-field"><small>{label}</small><strong>{value || "—"}</strong></div>;
}

export function DetailContent({ detail }: { detail: TradeDetailPayload["data"] }) {
  const trade = detail.trade;
  const fx=trade.fxForwardEconomics;
  const option=trade.optionEconomics;
  const product=trade.productEconomics;
  const genericSwap=bookedSwapFacts(trade);
  const instrumentName=genericSwap?product!.terms.name:trade.instrumentName??trade.subjectName;
  return (
    <>
      {product?<section className="detail-card"><h2>{product.terms.kind==='SWAP'?'Swap':product.terms.kind==='BOND'?'Bond':product.terms.kind==='FUTURE'?'Future':'Structured security'} · booking snapshot</h2><div className="detail-fields"><Field label="Instrument at booking" value={product.terms.name}/><Field label="Execution route" value={product.terms.executionRoute}/><Field label="Quoted execution price" value={`${formatTradeExactDecimal(trade.executionPrice)} · ${product.terms.convention?.priceBasis}`}/><Field label={genericSwap?"Booked nominal":"Quantity"} value={genericSwap?`${formatTradeExactDecimal(genericSwap.bookedNotional)} ${product.terms.currency}`:`${formatTradeExactDecimal(trade.quantity.replace(/^-/,'') )} ${trade.quantityUnit}`}/><Field label={product.amountKind==='ENTRY_REFERENCE_VALUE'?'Entry reference value (not a payment)':product.amountKind==='CONSIDERATION'?'Gross consideration':'Reference contract value (not a payment)'} value={`${product.direction??''} ${formatTradeExactDecimal(product.amount)} ${product.terms.currency}`}/><Field label="Terms fingerprint" value={product.terms.termsFingerprint}/><Field label="Source evidence" value={product.terms.convention?.sourceReference}/>{product.terms.convention?.kind==='FUTURE'?<><Field label="Contract month" value={product.terms.contractMonth}/><Field label="Underlying" value={product.terms.underlyingName}/><Field label="Contract multiplier" value={`${product.terms.convention.monetaryMultiplier} ${product.terms.currency}/point`}/><Field label="Contracts per listed unit" value={product.terms.listingUnitMultiplier==null?null:String(product.terms.listingUnitMultiplier)}/><Field label="Single-fill price tick" value={`${product.terms.convention.tickSize} index points`}/><Field label="Tick value per contract" value={`${productAmount(product.terms,'1',String(product.terms.convention.tickSize))} ${product.terms.currency}`}/><Field label="Last trading instant" value={product.terms.convention.lastTradingAtUtc}/><Field label="Final contract settlement" value={product.terms.convention.finalSettlementDate}/><Field label="Execution intent" value={trade.positionEffect}/></>:product.terms.convention?.kind==='STRUCTURED_PRODUCT'?<><Field label="Denomination" value={product.terms.convention.denomination?String(product.terms.convention.denomination):null}/><Field label="Accrual treatment" value={product.terms.convention.accrual}/><Field label="Maturity" value={product.terms.maturityDate}/></>:null}{product.terms.swapDetails&&!genericSwap?<><Field label="Performance reference" value={product.terms.swapDetails.performanceReferenceName}/><Field label="Canonical performance direction" value={product.terms.swapDetails.performanceDirection}/><Field label="Return treatment" value={product.terms.swapDetails.returnProfileCode}/><Field label="Funding reference" value={product.terms.swapDetails.fundingReferenceName}/><Field label="Canonical funding direction" value={product.terms.swapDetails.fundingDirection}/><Field label="Funding spread (decimal)" value={String(product.terms.swapDetails.fundingSpread)}/><Field label="Swap effective date" value={product.terms.swapDetails.effectiveDate}/><Field label="Maturity" value={product.terms.maturityDate}/></>:null}{product.bondDetails?<><Field label="Quoted price type" value={product.bondDetails.priceType}/><Field label="Clean consideration" value={`${product.bondDetails.cleanAmount} ${product.terms.currency}`}/><Field label="Total signed accrued interest" value={`${product.bondDetails.accruedInterestAmount} ${product.terms.currency}`}/><Field label="Dirty consideration before fees" value={`${product.bondDetails.dirtyAmount} ${product.terms.currency}`}/><Field label="Settlement/accrual evidence" value={product.bondDetails.settlementEvidence}/></>:null}<Field label="Quote divisor" value={String(product.terms.convention?.quoteFactor)}/></div><p>Immutable booking facts, not current master data. {product.amountKind==='ENTRY_REFERENCE_VALUE'?'Entry reference value is not independently verified MTM or a payment. SELL reverses both canonical legs. No cash trade or settlement instruction was generated.':product.amountKind==='REFERENCE_CONTRACT_VALUE'?'OPEN/CLOSE is execution intent, not position verification. No premium, purchase payment, margin or daily valuation is posted.':'One parent security trade; payoff components are not separate bookings.'}</p></section>:null}
      {genericSwap?<SwapTermsFacts terms={genericSwap.terms} labels={genericSwap.labels}/>:null}
      {option?<section className="detail-card"><h2>Option · booking snapshot</h2><div className="detail-fields"><Field label="Execution intent" value={trade.positionEffect}/><Field label="Option" value={`${option.terms.optionType} · ${option.terms.exerciseStyle}`}/><Field label="Strike" value={`${option.terms.strike} ${option.terms.strikeCurrency}`}/><Field label="Expiry" value={option.terms.expiryDate}/><Field label="Last trading instant" value={option.terms.lastTradingAtUtc}/><Field label="Exercise settlement" value={option.terms.settlementMethod}/><Field label="Deliverable units" value={option.terms.deliverableUnits}/><Field label="Premium multiplier" value={option.terms.premiumMultiplier}/><Field label="Quote factor" value={option.terms.quoteFactor}/><Field label="Gross premium" value={`${option.premiumDirection} ${formatTradeExactDecimal(option.grossPremium)} ${option.terms.premiumCurrency}`}/><Field label="Premium settlement date" value={trade.settlementDate}/><Field label="Terms fingerprint" value={option.terms.termsFingerprint}/></div><p>Immutable booking facts. OPEN/CLOSE is execution intent, not position verification, exercise, assignment or cash posting.</p></section>:null}
      {fx?<section className="detail-card"><h2>FX-forward obligations · booking snapshot</h2><div className="detail-fields"><Field label="Base currency" value={fx.baseCurrency}/><Field label="Quote currency" value={fx.quoteCurrency}/><Field label="Contract settlement date" value={fx.settlementDate}/><Field label="Receive at settlement" value={`${formatTradeExactDecimal(fx.receiveAmount)} ${fx.receiveCurrency}`}/><Field label="Pay at settlement" value={`${formatTradeExactDecimal(fx.payAmount)} ${fx.payCurrency}`}/><Field label="Terms fingerprint" value={fx.termsFingerprint}/></div><p>Immutable booking economics, not current instrument terms, settlement postings or daily valuation.</p></section>:null}
      <section className="detail-card">
        <div className="detail-card-heading"><div><p className="eyebrow">RECORDED TRADE · {trade.lifecycleStatus}</p><h2>{instrumentName}</h2><p className="muted">{trade.listingSymbol ? `${trade.listingSymbol} · ${trade.venueMic ?? "venue unavailable"}` : "Instrument-level / OTC subject"}</p></div><span className="quality">{trade.tradeType}</span></div>
        <div className="detail-fields"><Field label="Trade ID" value={trade.tradeId} /><Field label="Portfolio" value={`${trade.strategyCode} · ${trade.strategyName}`} /><Field label="Side" value={tradeDirection(trade.quantity)} /><Field label={trade.fxForwardEconomics?"Base-currency amount":option?"Contracts":"Quantity"} value={`${(trade.instrumentType==="FX_FORWARD"||option||product?formatTradeExactDecimal:formatTradeNumber)(trade.instrumentType==="FX_FORWARD"||option||product?trade.quantity.replace(/^-/, ""):trade.quantity)} ${trade.fxForwardEconomics?.baseCurrency??trade.quantityUnit}`} /><Field label={trade.fxForwardEconomics?"Agreed forward rate":option?"Executed premium (quoted units)":"Execution price"} value={`${(trade.instrumentType==="FX_FORWARD"||option||product?formatTradeExactDecimal:formatTradeNumber)(trade.executionPrice)} ${trade.fxForwardEconomics?.quoteConvention??(option?`quoted units · quote factor ${option.terms.quoteFactor} (${option.terms.premiumCurrency})`:product?`${product.terms.convention?.priceBasis} (quote currency ${product.terms.currency})`:trade.priceCurrency ?? "")}`} /><Field label="Price basis" value={trade.priceBasis} /><Field label="Trade time (UTC)" value={formatTradeDateTime(trade.tradeDatetimeUtc)} /><Field label="Valuation effective date (UTC)" value={trade.valuationEffectiveDate ?? trade.tradeDatetimeUtc.slice(0,10)} /><Field label="Valuation date basis" value={trade.valuationDateBasis ?? "LEGACY_UTC_TRADE_DATE"} /><Field label="Valuation override reason" value={trade.valuationOverrideReason} /><Field label={option?"Premium settlement date":"Settlement date"} value={product?.terms.kind==='SWAP'?'Not applicable (no automatic payment)':product?.terms.kind==='FUTURE'?'Not applicable (contract dates above)':trade.settlementDate} /><Field label="Execution venue" value={trade.venueName ?? trade.venueMic ?? (trade.instrumentType==="FX_FORWARD"?"OTC":null)} /><Field label="Execution channel" value={trade.executionChannel} /></div>
      </section>
      <section className="detail-card"><h2>Booking metadata</h2><div className="detail-fields"><Field label="Trade purpose" value={trade.tradePurpose} /><Field label="Market activity" value={trade.marketActivity} /><Field label="Source system" value={trade.sourceSystemId} /><Field label="Source received (UTC)" value={trade.sourceReceivedAtUtc ? formatTradeDateTime(trade.sourceReceivedAtUtc) : null} /><Field label="Dealing capacity" value={trade.dealingCapacity} /><Field label="Comment" value={trade.comment} /></div></section>
      <section className="detail-card"><h2>Trade properties and tags</h2><div className="detail-fields">{(detail.properties??[]).map(property=><Field key={property.definitionId} label={`${property.label} (${property.valueType}${property.recordVersion?`, record v${property.recordVersion}`:""})`} value={displayTradeProperty(property.valueType,property.value,property.displayValue)}/>)}<Field label="Trade tags" value={(detail.tags??[]).map(tag=>tag.label).join(", ")||"None"}/></div>{!detail.properties?.length?<p className="muted">No custom trade properties recorded.</p>:null}{detail.traderName?<div className="detail-fields"><Field label="Trader name" value={detail.traderName}/></div>:null}</section>
      <div className="detail-columns">
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">PARTIES &amp; PEOPLE</p><h2>Who is involved</h2></div></div><div className="party-list">{detail.parties.map((party) => <div className="party-row" key={party.tradePartyRoleId}><div><strong>{party.partyName}</strong><small>{party.role}</small></div><code>{party.organisationId ?? party.personId ?? "—"}</code></div>)}{trade.traderPersonId ? <div className="party-row"><div><strong>Trader</strong><small>Primary trader person</small></div><code>{trade.traderPersonId}</code></div> : null}<div className="party-row"><div><strong>Booked by</strong><small>Authenticated account</small></div><code>{trade.bookedByUserAccountId}</code></div></div></section>
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">FEES</p><h2>Charges &amp; revenue</h2></div></div>{detail.fees.length ? <div className="fee-list">{detail.fees.map((fee) => <div className="fee-row" key={fee.tradeFeeId}><div><strong>{fee.feeType}</strong><small>{fee.payerOrganisationName ?? "Unknown payer"} → {fee.recipientOrganisationName ?? "Unknown recipient"}</small></div><strong>{formatTradeNumber(fee.feeAmount)} {fee.feeCurrency ?? ""}</strong><small>{fee.feeRate ?? "—"} {fee.feeRateUnit ?? ""} · {fee.status}</small></div>)}</div> : <p className="muted">No fee records.</p>}</section>
      </div>
      <div className="detail-columns">
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">EXTERNAL REFERENCES</p><h2>Source identifiers</h2></div></div>{detail.externalReferences.length ? <div className="reference-list">{detail.externalReferences.map((reference) => <div className="reference-row" key={reference.tradeExternalReferenceId}><strong>{reference.referenceType}</strong><code>{reference.referenceValue}</code><small>{reference.sourceSystemId ?? "—"}</small></div>)}</div> : <p className="muted">No external references.</p>}</section>
        <section className="detail-card"><div className="detail-card-heading"><div><p className="eyebrow">LIFECYCLE</p><h2>Audit events</h2></div></div>{detail.lifecycleEvents.length ? <div className="event-list">{detail.lifecycleEvents.map((event) => {const links=bookingCorrectionLinks(event);return <div className="event-row" key={event.tradeLifecycleEventId}><div><strong>{event.sequenceNo}. {event.eventType}</strong><small>Effective (UTC): {formatTradeDateTime(event.eventDatetimeUtc)}</small><small>Recorded (UTC): {formatTradeDateTime(event.recordedAtUtc)} · {event.recordedByUserAccountId}</small><small>{event.sourceSystemId ?? "internal"}</small>{event.eventType==='FX_DELIVERY'?<DeliveryEventFacts raw={event.eventPayload}/>:null}{links?<><p>{links.reason}</p><Link href={`/trades/${links.originalTradeId}`}>Original booking</Link>{links.replacementTradeId?<>{" · "}<Link href={`/trades/${links.replacementTradeId}`}>Replacement booking</Link></>:null}</>:null}</div><code>{event.sourceEventId ?? "—"}</code></div>;})}</div> : <p className="muted">No lifecycle events.</p>}</section>
      </div>
    </>
  );
}

export default async function TradeDetailPage({ params, searchParams }: { params: Promise<{ tradeId: string }>; searchParams: Promise<HistorySearchParams> }) {
  const { tradeId } = await params;
  const returnTo = safeHistoryReturn((await searchParams).returnTo);
  let context;
  let workspace;
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  let detail: TradeDetailPayload["data"] | null = null;
  let delivery:FxDeliveryProgress|null=null;
  let deliveryError='';
  let error = "";
  let sourceLabel = "LIVE API";
  try {
    detail = (await getBookedTradeDetail(context, tradeId)).data;
  } catch (caught) {
    error = describeMvpError(caught, "Booked trade");
    sourceLabel = caught instanceof MvpApiError && caught.status < 500
      ? caught.status === 404 ? "NOT FOUND" : [401,403].includes(caught.status) ? "ACCESS DENIED" : "REQUEST FAILED"
      : "API UNAVAILABLE";
  }
  const snapshotName=detail&&bookedSwapFacts(detail.trade)?detail.trade.productEconomics!.terms.name:undefined;
  if(detail?.trade.fxForwardEconomics&&detail.trade.lifecycleStatus==='BOOKED'){
    try{delivery=(await getFxDelivery(tradeId,context)).data;}
    catch{deliveryError='FX delivery evidence is unavailable or unsupported. Do not infer fulfilment from the booking or maturity date.';}
  }
  return (
    <WorkspaceShell sourceLabel={sourceLabel} moduleCodes={workspace.moduleCodes} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole}><main className="mvp-page">
      <header className="mvp-header"><div><p className="eyebrow">TRADE DETAIL</p><h1>{snapshotName ?? detail?.trade.instrumentName ?? "Booked execution"}</h1><p className="muted">Normalized parties, fees, source references and append-only lifecycle evidence.</p></div><span className={`synthetic-badge ${sourceLabel === "API UNAVAILABLE" ? "source-unavailable" : ""}`}>{sourceLabel}</span></header>
      <p className="back-line"><Link href={returnTo}>← Back to trade history</Link></p>
      {error ? <div role="alert" className="error-panel">{error}</div> : detail ? <DetailContent detail={detail} /> : <div className="error-panel">Booked trade not found.</div>}
      {deliveryError?<p role="alert" className="error-panel">{deliveryError}</p>:null}
      {delivery?<FxDeliveryControls key={`${context.tenantId}:${tradeId}:${delivery.expectedSequenceNo}`} progress={delivery} tenantId={context.tenantId} canWrite={workspace.permissionCodes?.includes('TRADE_CORRECT')??false}/>:null}
      {detail&&workspace.permissionCodes?.includes('TRADE_CORRECT')?<RecordCorrectionActions key={`${context.tenantId}:${tradeId}`} detail={detail} tenantId={context.tenantId} canReplace={workspace.permissionCodes.includes('TRADE_WRITE')}/>:null}
    </main></WorkspaceShell>
  );
}
