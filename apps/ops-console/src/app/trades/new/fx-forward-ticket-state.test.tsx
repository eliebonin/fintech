import {afterEach,expect,it,vi} from "vitest";
const harness=vi.hoisted(()=>({slots:[] as any[],cursor:0,effects:[] as (()=>unknown)[],send:vi.fn(),push:vi.fn()}));
vi.mock("react",async original=>{
  const actual=await original<typeof import("react")>();
  return {...actual,useState:(initial:any)=>{const i=harness.cursor++;if(!(i in harness.slots))harness.slots[i]=typeof initial==="function"?initial():initial;return [harness.slots[i],(value:any)=>{harness.slots[i]=typeof value==="function"?value(harness.slots[i]):value;}];},useRef:(initial:any)=>{const i=harness.cursor++;if(!(i in harness.slots))harness.slots[i]={current:initial};return harness.slots[i];},useEffect:(effect:()=>unknown)=>harness.effects.push(effect)};
});
vi.mock("next/navigation",()=>({useRouter:()=>({push:harness.push,refresh:vi.fn()})}));
vi.mock("@/lib/browser-api-client",async original=>({...await original<typeof import("@/lib/browser-api-client")>(),submitFxForwardTradeFromBff:harness.send}));
import {FxForwardTicket} from "./fx-forward-ticket";
import {PartyFields} from "./party-fields";
import {PropertyFields} from "./property-fields";
import {BffApiError} from "@/lib/api-errors";
const instrument={instrumentId:"instrument",name:"EUR/USD",baseCurrency:"EUR",quoteCurrency:"USD",quoteConvention:"USD_PER_EUR",agreedRate:"1.10",settlementDate:"2026-12-15",maturityDate:"2026-12-15",settlementType:"DELIVERABLE",termsFingerprint:"a".repeat(64),bookingEligible:true};
const context={tenantId:"tenant",bookedByUserAccountId:"actor",properties:[{definitionId:"decimal",code:"DECIMAL",label:"Numeric",description:null,valueType:"DECIMAL" as const,required:false,choices:[]}],tags:[]};
let correction:import('@/lib/trade-correction-model').BookingCorrection|undefined;
function render(){harness.cursor=0;harness.effects=[];return FxForwardTicket({initialInstrument:instrument,strategies:[{strategyId:"strategy",strategyCode:"TEST",displayName:"Test",status:"ACTIVE"}],context,correction});}
function find(node:any,predicate:(node:any)=>boolean):any {if(!node||typeof node!=="object")return;if(predicate(node))return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}}
const byId=(tree:any,id:string)=>find(tree,n=>n.props?.id===id);
const button=(tree:any,text:string)=>find(tree,n=>n.type==="button"&&n.props.children===text);
function review(){let tree=render();for(const [id,value] of [["strategyId","strategy"],["quantity","1000000"],["tradeDatetime","2026-10-01T10:00:00Z"]])byId(tree,id).props.onChange({target:{value}});find(tree,n=>n.type===PartyFields).props.onChange({counterpartyOrganisationId:"bank",counterpartyName:"Bank"});find(tree,n=>n.type===PropertyFields).props.onChange({properties:{decimal:"0"}});tree=render();find(tree,n=>n.type==="form").props.onSubmit({preventDefault(){}});return render();}
afterEach(()=>{correction=undefined;harness.slots=[];harness.cursor=0;harness.effects=[];harness.send.mockReset();harness.push.mockReset();vi.unstubAllGlobals();});
it('submits the confirmed correction context with the FX ticket',async()=>{correction={tradeId:'original',expectedSequenceNo:1,reason:'Wrong amount'};harness.send.mockResolvedValueOnce({data:{trade:{tradeId:'replacement'}}});await button(review(),'Confirm booking').props.onClick();expect(harness.send.mock.calls[0][0].correction).toEqual(correction);});
it("preserves custom zero through review and back-to-edit",()=>{const tree=review();button(tree,"Back to edit").props.onClick();expect(find(render(),n=>n.type===PropertyFields).props.draft.properties.decimal).toBe("0");});
it("retries an uncertain booking with exactly the frozen request/key/tenant",async()=>{
  harness.send.mockRejectedValueOnce(new BffApiError(503,"Unavailable")).mockResolvedValueOnce({data:{trade:{tradeId:"saved"}}});
  await button(review(),"Confirm booking").props.onClick();const retry=render();expect(button(retry,"Back to edit").props.disabled).toBe(true);await button(retry,"Retry unchanged booking").props.onClick();
  expect(harness.send).toHaveBeenCalledTimes(2);expect(harness.send.mock.calls[1]).toEqual(harness.send.mock.calls[0]);expect(harness.send.mock.calls[0][0].properties).toEqual([{definitionId:"decimal",value:"0"}]);expect(harness.push).toHaveBeenCalledWith("/trades/saved");
});
it("prevents repeated submission while the first request is in flight",async()=>{
  let finish:(value:any)=>void=()=>{};harness.send.mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const tree=review();const confirmation=button(tree,"Confirm booking");const first=confirmation.props.onClick();await confirmation.props.onClick();expect(harness.send).toHaveBeenCalledOnce();finish({data:{trade:{tradeId:"saved"}}});await first;
});
it("blocks a stale-terms conflict without creating a fresh retry",async()=>{
  harness.send.mockRejectedValueOnce(new BffApiError(409,"Reselect the contract","fx_forward.terms_changed"));
  await button(review(),"Confirm booking").props.onClick();const tree=render();expect(button(tree,"Confirm booking").props.disabled).toBe(true);expect(button(tree,"Back to edit").props.disabled).toBe(true);await button(tree,"Confirm booking").props.onClick();expect(harness.send).toHaveBeenCalledOnce();
});
it("guards sidebar and browser-back navigation after an edit",()=>{
  const handlers:Record<string,(e:any)=>void>={};const confirm=vi.fn(()=>false),pushState=vi.fn();
  vi.stubGlobal("window",{location:{href:"http://test/trades/new?product=FX_FORWARD"},history:{state:{__NA:true},pushState},confirm,alert:vi.fn(),addEventListener:(name:string,fn:any)=>handlers[name]=fn,removeEventListener:vi.fn()});
  vi.stubGlobal("document",{addEventListener:(name:string,fn:any)=>handlers[name]=fn,removeEventListener:vi.fn()});
  const tree=render();for(const effect of harness.effects)effect();byId(tree,"quantity").props.onChange({target:{value:"1"}});
  const prevent=vi.fn();handlers.click({target:{closest:()=>({target:"",hasAttribute:()=>false,getAttribute:()=>"/trades"})},preventDefault:prevent,stopPropagation:vi.fn()});expect(prevent).toHaveBeenCalledOnce();handlers.popstate({stopImmediatePropagation:vi.fn()});expect(pushState).toHaveBeenCalledOnce();
});
