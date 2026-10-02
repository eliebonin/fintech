import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { BookingReview } from "./booking-review";
vi.mock("next/navigation",()=>({useRouter:()=>({push:()=>{}})}));

describe("booking property review",()=>{
  it("uses Yes/No while retaining zero, exact decimals and the selected reference label",()=>{
    const properties=[
      {definitionId:"false",code:"FALSE",label:"Internal cross",valueType:"BOOLEAN" as const,required:false,choices:[],description:null},
      {definitionId:"true",code:"TRUE",label:"Client instructed",valueType:"BOOLEAN" as const,required:false,choices:[],description:null},
      {definitionId:"zero",code:"ZERO",label:"Allocation",valueType:"DECIMAL" as const,required:false,choices:[],description:null},
      {definitionId:"exact",code:"EXACT",label:"Precise",valueType:"DECIMAL" as const,required:false,choices:[],description:null},
      {definitionId:"reference",code:"REF",label:"Bucket",valueType:"REFERENCE" as const,required:false,choices:[],description:null,catalogueId:"catalogue"},
    ];
    const html=renderToStaticMarkup(<BookingReview listing={{referenceNodeId:"listing",canonicalName:"Example",marketVenueMic:"XLON",venueName:"London",tradingSymbol:"TEST",tradingCurrency:"GBP",status:"ACTIVE",isTradable:true}} strategies={[]} context={{tenantId:"tenant",bookedByUserAccountId:"actor",properties,tags:[]}} draft={{strategyId:"strategy",side:"BUY",quantity:"1",executionPrice:"1",tradeDatetime:"2026-10-01T10:00:00Z",settlementDate:"2026-10-05",tradePurpose:"INVESTMENT",properties:{false:false,true:true,zero:"0",exact:"0.123456789012",reference:"identity"},propertyLabels:{reference:"CORE — Original label"},tagIds:[],externalReferences:[]}}/>);
    for(const value of ["No","Yes","0","0.123456789012","CORE — Original label"])expect(html).toContain(`<dd>${value}</dd>`);
    expect(html).not.toContain("<dd>false</dd>");
  });
});
