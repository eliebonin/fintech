import { afterEach, expect, it, vi } from "vitest";

const effects=vi.hoisted(()=>[] as (()=>unknown)[]);
vi.mock("react",async importOriginal=>{
  const actual=await importOriginal<typeof import("react")>();
  return {...actual,useRef:(value:unknown)=>({current:value}),useState:(value:unknown)=>[typeof value==="function"?value():value,vi.fn()],useEffect:(effect:()=>unknown)=>effects.push(effect)};
});
vi.mock("next/navigation",()=>({useRouter:()=>({push:vi.fn()})}));
import { TradeTicket } from "./trade-ticket";

afterEach(()=>{effects.length=0;vi.unstubAllGlobals();});

it("guards actual ticket sidebar and browser-back handlers after an edit",()=>{
  const handlers:Record<string,(event:any)=>void>={};
  const confirm=vi.fn(()=>false),pushState=vi.fn();
  vi.stubGlobal("window",{location:{href:"http://test/trades/new"},history:{state:{__NA:true},pushState},confirm,alert:vi.fn(),addEventListener:(name:string,handler:any)=>handlers[name]=handler,removeEventListener:vi.fn()});
  vi.stubGlobal("document",{addEventListener:(name:string,handler:any)=>handlers[name]=handler,removeEventListener:vi.fn()});
  const tree=TradeTicket({listing:{referenceNodeId:"listing",canonicalName:"Cash",marketVenueMic:"XLON",venueName:"London",tradingSymbol:"TEST",tradingCurrency:"GBP",status:"ACTIVE",isTradable:true},strategies:[],context:{tenantId:"tenant",bookedByUserAccountId:"actor",properties:[],tags:[]}});
  for(const effect of effects)effect();
  function find(node:any):any {
    if(!node||typeof node!=="object")return;
    if(node.props?.id==="quantity")return node;
    for(const child of [node.props?.children].flat(Infinity)){const match=find(child);if(match)return match;}
  }
  find(tree).props.onChange({target:{value:"10"}});
  const stop=vi.fn(),prevent=vi.fn();
  handlers.click({target:{closest:()=>({target:"",hasAttribute:()=>false,getAttribute:()=>"/trades"})},preventDefault:prevent,stopPropagation:stop});
  expect(confirm).toHaveBeenCalledWith("Discard the unbooked ticket?");
  expect(prevent).toHaveBeenCalledOnce();
  expect(stop).toHaveBeenCalledOnce();
  const stopBack=vi.fn();
  handlers.popstate({stopImmediatePropagation:stopBack});
  expect(stopBack).toHaveBeenCalledOnce();
  expect(pushState).toHaveBeenCalledWith({__NA:true},"","http://test/trades/new");
});
