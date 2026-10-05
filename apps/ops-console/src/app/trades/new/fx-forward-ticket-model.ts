import type { FxForwardBookingInstrumentView, FxForwardBookingRequest, TradeBookingContext } from "@/lib/browser-api-client";
import { grossConsideration, validateTradeAnnotations, type EnrichedTicketDraft, type TicketError } from "./ticket-model";
import {multiplyBookingDecimals} from '@/lib/booking-decimal';
export type FxForwardTicketDraft=Omit<EnrichedTicketDraft,"executionPrice"|"settlementDate"|"marketActivity">;
export function previewFxForwardObligations(instrument:FxForwardBookingInstrumentView,side:"BUY"|"SELL",quantity:string) {
  const amount=multiplyBookingDecimals([quantity,instrument.agreedRate??""]);
  return side==="BUY"?{receiveCurrency:instrument.baseCurrency,receiveAmount:quantity,payCurrency:instrument.quoteCurrency,payAmount:amount}:{receiveCurrency:instrument.quoteCurrency,receiveAmount:amount,payCurrency:instrument.baseCurrency,payAmount:quantity};
}
export function validateFxForwardTicketDraft(instrument:FxForwardBookingInstrumentView,draft:FxForwardTicketDraft,context:TradeBookingContext):TicketError[] {
  const errors=validateTradeAnnotations(draft,context);
  if(!instrument.bookingEligible||!instrument.termsFingerprint)errors.push({field:"instrumentId",message:instrument.ineligibilityMessage??"This contract is not eligible for booking."});
  if(!draft.strategyId)errors.push({field:"strategyId",message:"Select a strategy."});
  if(!draft.counterpartyOrganisationId)errors.push({field:"counterpartyOrganisationId",message:"Select a governed counterparty."});
  if(!/^\d+(?:\.\d{1,12})?$/.test(draft.quantity)||Number(draft.quantity)<=0||draft.quantity.split(".")[0].replace(/^0+/,"").length>18)errors.push({field:"quantity",message:"Enter a positive base amount with at most 18 integer and 12 fractional digits."});
  const timestamp=new Date(draft.tradeDatetime);
  if(!/(?:Z|[+-]\d{2}:\d{2})$/.test(draft.tradeDatetime)||Number.isNaN(timestamp.getTime())||(instrument.settlementDate&&timestamp.toISOString().slice(0,10)>instrument.settlementDate))errors.push({field:"tradeDatetime",message:"Enter a timezone-aware execution timestamp on or before settlement."});
  return errors;
}
export function buildFxForwardTicketPayload(instrument:FxForwardBookingInstrumentView,draft:FxForwardTicketDraft):FxForwardBookingRequest {
  return {instrumentId:instrument.instrumentId,expectedTermsFingerprint:instrument.termsFingerprint??"",strategyId:draft.strategyId,side:draft.side,quantity:draft.quantity,tradeDatetime:draft.tradeDatetime,counterpartyOrganisationId:draft.counterpartyOrganisationId??"",executingBrokerOrganisationId:draft.executingBrokerOrganisationId||null,traderPersonId:draft.traderPersonId||null,tradePurpose:draft.tradePurpose,comment:draft.comment?.trim()||null,externalReference:draft.externalReference?.trim()||null,tagIds:draft.tagIds,properties:Object.entries(draft.properties).flatMap(([definitionId,value])=>value===undefined||(typeof value==="string"&&!value.trim())?[]:[{definitionId,value:typeof value==="string"?value.trim():value}]),externalReferences:draft.externalReferences.map(r=>({...r,referenceValue:r.referenceValue.trim(),sourceSystemId:r.sourceSystemId?.trim()||null}))};
}
