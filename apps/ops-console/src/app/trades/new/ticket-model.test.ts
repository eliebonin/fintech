import { describe, expect, it } from "vitest";
import { grossConsideration, buildEnrichedTicketPayload, validateEnrichedTicketDraft, freezeBookingSubmission, bookingFailureMode, revalidateEditedFields, editedTicketFields } from "./ticket-model";
import { BffApiError } from "@/lib/api-errors";

const listing = {referenceNodeId:"listing", canonicalName:"Test", marketVenueMic:"XLON", venueName:"London", tradingSymbol:"TEST", tradingCurrency:"GBP", status:"ACTIVE", isTradable:true};
const context = {tenantId:"tenant", bookedByUserAccountId:"actor", properties:[{definitionId:"flag",code:"FLAG",label:"Flag",valueType:"BOOLEAN" as const,required:true,choices:[],description:null}],tags:[]};
const draft = {strategyId:"strategy", side:"BUY" as const,quantity:"0.1",executionPrice:"0.2",tradeDatetime:"2026-09-30T10:00:00Z",settlementDate:"2026-10-02",tradePurpose:"INVESTMENT" as const,properties:{flag:false},tagIds:[],externalReferences:[]};

describe("enriched ticket model", () => {
  it("preserves a server settlement error when only trade time changes",()=>{
    const values={tradeDatetime:"2026-09-30T11:00:00Z",settlementDate:draft.settlementDate};
    const next={...draft,...values};
    const errors=[{field:"settlementDate",message:"Server calendar restriction"}];
    const edited=editedTicketFields(draft,next,values);
    expect(edited).toEqual(["tradeDatetime"]);
    expect(revalidateEditedFields(errors,next,context,edited)).toEqual(errors);
  });
  it("preserves untouched reference errors and accounts for removed/index-shifted rows",()=>{
    const before={...draft,externalReferences:[{referenceType:"CLIENT_REFERENCE" as const,referenceValue:"first"},{referenceType:"BROKER_REFERENCE" as const,referenceValue:"second"}]};
    const values={externalReferences:[{...before.externalReferences[0],referenceValue:"changed"},before.externalReferences[1]]};
    const next={...before,...values};
    const errors=[{field:"reference-1",message:"Server reference restriction"}];
    const edited=editedTicketFields(before,next,values);
    expect(edited).toEqual(["reference-0"]);
    expect(revalidateEditedFields(errors,next,context,edited)).toEqual(errors);
    const removed={externalReferences:[before.externalReferences[1]]};
    expect(editedTicketFields(before,{...before,...removed},removed)).toEqual(["reference-0","reference-1"]);
  });
  it("revalidates only previously errored edited fields and preserves unrelated server errors",()=>{
    const errors=[{field:"properties.flag",message:"Required"},{field:"quantity",message:"Server quantity constraint"}];
    expect(revalidateEditedFields(errors,draft,context,["properties.flag"])).toEqual([errors[1]]);
    expect(revalidateEditedFields(errors,{...draft,properties:{}},context,["properties.flag"])).toEqual([errors[1],{field:"properties.flag",message:"Flag is required."}]);
  });
  it("keeps an invalid edited quantity visible even while another basic field is invalid",()=>{
    const errors=[{field:"quantity",message:"Invalid quantity"},{field:"strategyId",message:"Select a strategy."}];
    expect(revalidateEditedFields(errors,{...draft,strategyId:"",quantity:"-1"},context,["quantity"])).toEqual([
      errors[1],{field:"quantity",message:"Quantity must be greater than zero."},
    ]);
  });
  it("rejects a stale embedded-choice ticket instead of reviving the legacy workflow",()=>{
    const legacy={...context,properties:[{...context.properties[0],valueType:"CHOICE" as const,choices:["CORE"]}]};
    expect(validateEnrichedTicketDraft({...draft,properties:{flag:"CORE"}},legacy)).toContainEqual({field:"properties.flag",message:"This legacy dropdown has been replaced. Reopen the booking ticket."});
  });
  it("sends governed identities, not their mutable display labels",()=>{
    const id="00000000-0000-7000-8000-000000000001";
    const governed={...context,properties:[{...context.properties[0],valueType:"REFERENCE" as const,catalogueId:"catalogue"}]};
    const selection={...draft,properties:{flag:id},propertyLabels:{flag:"CORE — Core allocation"}};
    expect(validateEnrichedTicketDraft(selection,governed)).toEqual([]);
    expect(buildEnrichedTicketPayload(listing,selection,governed).properties).toEqual([{definitionId:"flag",value:id}]);
    expect(validateEnrichedTicketDraft({...selection,properties:{flag:"Core allocation"}},governed)[0].field).toBe("properties.flag");
  });
  it("rejects fractional values for integer properties",()=>{
    const integers={...context,properties:[{...context.properties[0],valueType:"INTEGER" as const}]};
    expect(validateEnrichedTicketDraft({...draft,properties:{flag:"12"}},integers)).toEqual([]);
    expect(validateEnrichedTicketDraft({...draft,properties:{flag:"12.5"}},integers)[0].field).toBe("properties.flag");
  });
  it("freezes the original payload, key and tenant for an unchanged retry", () => {
    const payload=buildEnrichedTicketPayload(listing,draft,context);
    const snapshot=freezeBookingSubmission(payload,"original-key","original-tenant");
    payload.properties![0].value=true;
    payload.quantity="999";
    expect(snapshot.payload.quantity).toBe("0.1");
    expect(snapshot.payload.properties![0].value).toBe(false);
    expect(snapshot.key).toBe("original-key");
    expect(snapshot.expectedTenantId).toBe("original-tenant");
  });
  it("keeps uncertain failures in retry, conflicts blocked, known rejection editable", () => {
    expect(bookingFailureMode(new Error("network"))).toBe("RETRY_REQUIRED");
    expect(bookingFailureMode(new BffApiError(503,"Unavailable"))).toBe("RETRY_REQUIRED");
    expect(bookingFailureMode(new BffApiError(409,"Conflict"))).toBe("BLOCKED");
    expect(bookingFailureMode(new BffApiError(422,"Invalid"))).toBe("EDITING");
  });
  it.each([["0.1","0.2","0.02"],["150","10.55","1582.5"],["999999999999999999","0.01","9999999999999999.99"]])("multiplies %s by %s exactly", (q,p,want) => {expect(grossConsideration(q,p)).toBe(want);});
  it("retains false as a real property value in the payload", () => {
    expect(buildEnrichedTicketPayload(listing,draft,context).properties).toEqual([{definitionId:"flag",value:false}]);
    expect(validateEnrichedTicketDraft(draft,context)).toEqual([]);
  });
  it("identifies missing required properties and invalid purpose", () => {
    expect(validateEnrichedTicketDraft({...draft,properties:{},tradePurpose:"OTHER"},context).map(e=>e.field)).toEqual(expect.arrayContaining(["properties.flag","comment"]));
  });
  it("treats whitespace properties as absent and rejects unknown property IDs", () => {
    const textContext={...context,properties:[{...context.properties[0],valueType:"TEXT" as const}]};
    expect(validateEnrichedTicketDraft({...draft,properties:{flag:"   "}},textContext).map(e=>e.field)).toContain("properties.flag");
    expect(buildEnrichedTicketPayload(listing,{...draft,properties:{flag:"   "}},{...textContext,properties:[{...textContext.properties[0],required:false}]}).properties).toEqual([]);
    expect(validateEnrichedTicketDraft({...draft,properties:{flag:false,unknown:"value"}},context).map(e=>e.field)).toContain("properties.unknown");
  });
});
