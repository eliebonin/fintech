import type { OptionBookingListingView,OptionBookingRequest,TradeBookingContext } from '@/lib/browser-api-client';
import { grossConsideration,validateTradeAnnotations,type EnrichedTicketDraft,type TicketError } from './ticket-model';
import {multiplyBookingDecimals,exactBookingAmount} from '@/lib/booking-decimal';
export type OptionTicketDraft=EnrichedTicketDraft&{positionEffect:'OPEN'|'CLOSE'};

/** Exact base-10 arithmetic. This preview never rounds an unrepresentable amount. */
export function previewOptionPremium(terms:OptionBookingListingView,quantity:string,premium:string):string {
  const product=multiplyBookingDecimals([grossConsideration(quantity,premium),terms.premiumMultiplier??'']);
  const factor=terms.quoteFactor??'';
  return exactBookingAmount([product],factor,{integerDigits:80,fractionDigits:80});
}
export function validateOptionTicketDraft(terms:OptionBookingListingView,draft:OptionTicketDraft,context:TradeBookingContext):TicketError[] {
  const errors=validateTradeAnnotations(draft,context);
  if(!terms.bookingEligible||!terms.termsFingerprint)errors.push({field:'listingId',message:terms.ineligibilityMessage??'Select an eligible option listing.'});
  if(!draft.strategyId)errors.push({field:'strategyId',message:'Select a strategy.'});
  if(!/^\d{1,18}$/.test(draft.quantity)||BigInt(draft.quantity||'0')<=BigInt(0))errors.push({field:'quantity',message:'Enter a positive integer number of contracts (at most 18 digits).'});
  if(!/^\d{1,18}(?:\.\d{1,12})?$/.test(draft.executionPrice)||previewOptionPremium(terms,draft.quantity,draft.executionPrice)==='—')errors.push({field:'executionPrice',message:'Enter a non-negative premium with exact supported precision.'});
  if(!['OPEN','CLOSE'].includes(draft.positionEffect))errors.push({field:'positionEffect',message:'Select OPEN or CLOSE.'});
  const timestamp=new Date(draft.tradeDatetime);
  const validTime=/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(draft.tradeDatetime)&&!Number.isNaN(timestamp.getTime());
  if(!validTime||!terms.lastTradingAtUtc||timestamp>new Date(terms.lastTradingAtUtc))errors.push({field:'tradeDatetime',message:'Enter an execution time with timezone on or before the approved cutoff.'});
  const settlement=new Date(`${draft.settlementDate}T00:00:00Z`);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(draft.settlementDate)||Number.isNaN(settlement.getTime())||settlement.toISOString().slice(0,10)!==draft.settlementDate||(validTime&&draft.settlementDate<timestamp.toISOString().slice(0,10)))errors.push({field:'settlementDate',message:'Enter the actual premium settlement date, on or after execution.'});
  return errors;
}
export function buildOptionTicketPayload(terms:OptionBookingListingView,draft:OptionTicketDraft):OptionBookingRequest {
  return {listingId:terms.listingId,expectedTermsFingerprint:terms.termsFingerprint??'',strategyId:draft.strategyId,side:draft.side,positionEffect:draft.positionEffect,quantity:draft.quantity,executionPrice:draft.executionPrice,tradeDatetime:draft.tradeDatetime,settlementDate:draft.settlementDate,counterpartyOrganisationId:draft.counterpartyOrganisationId||null,executingBrokerOrganisationId:draft.executingBrokerOrganisationId||null,traderPersonId:draft.traderPersonId||null,tradePurpose:draft.tradePurpose,marketActivity:draft.marketActivity||null,comment:draft.comment?.trim()||null,tagIds:draft.tagIds,properties:Object.entries(draft.properties).flatMap(([definitionId,value])=>value===undefined||(typeof value==='string'&&!value.trim())?[]:[{definitionId,value:typeof value==='string'?value.trim():value}]),externalReferences:draft.externalReferences.map(r=>({...r,referenceValue:r.referenceValue.trim(),sourceSystemId:r.sourceSystemId?.trim()||null}))};
}
