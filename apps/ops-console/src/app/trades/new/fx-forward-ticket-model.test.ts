import { expect, it } from "vitest";
import { buildFxForwardTicketPayload, previewFxForwardObligations, validateFxForwardTicketDraft, type FxForwardTicketDraft } from "./fx-forward-ticket-model";
import type { FxForwardBookingInstrumentView } from "@/lib/browser-api-client";
export const instrument: FxForwardBookingInstrumentView = {instrumentId:"00000000-0000-0000-0000-000000000001",name:"EUR/USD contract",baseCurrency:"EUR",quoteCurrency:"USD",quoteConvention:"USD_PER_EUR",agreedRate:"1.10",maturityDate:"2026-12-15",settlementDate:"2026-12-15",settlementType:"DELIVERABLE",termsFingerprint:"a".repeat(64),bookingEligible:true};
export const draft: FxForwardTicketDraft = {strategyId:"strategy",side:"BUY",quantity:"1000000",tradeDatetime:"2026-10-01T10:00:00Z",counterpartyOrganisationId:"bank",tradePurpose:"HEDGING",properties:{},tagIds:[],externalReferences:[]};
const context={tenantId:"tenant",bookedByUserAccountId:"actor",properties:[],tags:[]};
it("derives BUY and SELL obligations without creating a second trade",()=>{
 expect(previewFxForwardObligations(instrument,"BUY","1000000")).toEqual({receiveCurrency:"EUR",receiveAmount:"1000000",payCurrency:"USD",payAmount:"1100000"});
 expect(previewFxForwardObligations(instrument,"SELL","1000000")).toEqual({receiveCurrency:"USD",receiveAmount:"1100000",payCurrency:"EUR",payAmount:"1000000"});
});
it("retains decimal precision in quote obligations",()=>expect(previewFxForwardObligations({...instrument,agreedRate:"1.123456789012"},"BUY","0.000001").payAmount).toBe("0.000001123456789012"));
it("submits inherited identity and fingerprint, never cash overrides",()=>{
 const payload=buildFxForwardTicketPayload(instrument,draft);
 expect(payload.instrumentId).toBe(instrument.instrumentId);expect(payload.expectedTermsFingerprint).toBe("a".repeat(64));
 for(const key of ["listingId","executionPrice","settlementDate","marketActivity"])expect(payload).not.toHaveProperty(key);
});
it.each(["0","-1","0.0000000000001","1000000000000000000"])("rejects invalid base quantity %s",quantity=>expect(validateFxForwardTicketDraft(instrument,{...draft,quantity},context).some(e=>e.field==="quantity")).toBe(true));
it("requires counterparty and rejects ineligible instrument",()=>{
 expect(validateFxForwardTicketDraft(instrument,{...draft,counterpartyOrganisationId:""},context).some(e=>e.field==="counterpartyOrganisationId")).toBe(true);
 expect(validateFxForwardTicketDraft({...instrument,bookingEligible:false},draft,context).some(e=>e.field==="instrumentId")).toBe(true);
});
it("requires an offset and cannot execute after settlement",()=>{
 expect(validateFxForwardTicketDraft(instrument,{...draft,tradeDatetime:"2026-10-01T10:00:00"},context).some(e=>e.field==="tradeDatetime")).toBe(true);
 expect(validateFxForwardTicketDraft(instrument,{...draft,tradeDatetime:"2026-12-16T10:00:00Z"},context).some(e=>e.field==="tradeDatetime")).toBe(true);
});
