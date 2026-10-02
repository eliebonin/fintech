import { describe, expect, it } from "vitest";
import { displayTradeProperty } from "./trade-property-display";

describe("trade property display",()=>{
  it.each([
    ["BOOLEAN",false,undefined,"No"],
    ["BOOLEAN",true,undefined,"Yes"],
    ["BOOLEAN",undefined,undefined,"Not specified"],
    ["TEXT","",undefined,"Not specified"],
    ["DECIMAL","0",undefined,"0"],
    ["DECIMAL","0.123456789012",undefined,"0.123456789012"],
    ["REFERENCE","identity","Booked label","Booked label"],
  ])("formats %s %s",(type,value,label,expected)=>{
    expect(displayTradeProperty(type,value,label)).toBe(expected);
  });
});
