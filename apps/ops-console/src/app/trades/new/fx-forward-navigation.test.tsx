import {afterEach,expect,it,vi} from 'vitest';
const effects=vi.hoisted(()=>[] as (()=>unknown)[]);
vi.mock('react',async original=>({...await original<typeof import('react')>(),useRef:(value:any)=>({current:value}),useState:(value:any)=>[typeof value==='function'?value():value,vi.fn()],useEffect:(effect:()=>unknown)=>effects.push(effect)}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn(),refresh:vi.fn()})}));
import {FxForwardTicket} from './fx-forward-ticket';
afterEach(()=>{effects.length=0;vi.unstubAllGlobals();});
function setup(discard:boolean){
  const handlers:Record<string,(event:any)=>void>={};const confirm=vi.fn(()=>discard),pushState=vi.fn();
  vi.stubGlobal('window',{location:{href:'http://test/trades/new?product=FX_FORWARD'},history:{state:{__NA:true},pushState},confirm,alert:vi.fn(),addEventListener:(name:string,handler:any)=>handlers[name]=handler,removeEventListener:vi.fn()});
  vi.stubGlobal('document',{addEventListener:(name:string,handler:any)=>handlers[name]=handler,removeEventListener:vi.fn()});
  const tree=FxForwardTicket({initialInstrument:{instrumentId:'forward',name:'Forward',baseCurrency:'EUR',quoteCurrency:'USD',quoteConvention:'USD_PER_EUR',agreedRate:'1.1',settlementDate:'2026-12-15',maturityDate:'2026-12-15',bookingEligible:true,termsFingerprint:'a'.repeat(64)} as any,strategies:[],context:{tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]}});
  for(const effect of effects)effect();
  function find(node:any):any{if(!node||typeof node!=='object')return;if(node.props?.id==='quantity')return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child);if(found)return found;}}
  find(tree).props.onChange({target:{value:'100'}});
  const prevent=vi.fn(),stop=vi.fn();
  const event={target:{closest:()=>({target:'',hasAttribute:()=>false,getAttribute:()=>'/trades/new?product=OPTION'})},preventDefault:prevent,stopPropagation:stop};
  return {handlers,confirm,pushState,prevent,stop,event};
}
it('retains the FX draft when cross-product discard is declined',()=>{const x=setup(false);x.handlers.click(x.event);expect(x.confirm).toHaveBeenCalledWith('Discard the unbooked ticket?');expect(x.prevent).toHaveBeenCalledOnce();const stop=vi.fn();x.handlers.popstate({stopImmediatePropagation:stop});expect(stop).toHaveBeenCalledOnce();expect(x.pushState).toHaveBeenCalled();});
it('permits the switch and clears unload protection after discard is confirmed',()=>{const x=setup(true);x.handlers.click(x.event);expect(x.prevent).not.toHaveBeenCalled();const prevent=vi.fn();x.handlers.beforeunload({preventDefault:prevent});expect(prevent).not.toHaveBeenCalled();x.handlers.click(x.event);expect(x.confirm).toHaveBeenCalledOnce();});
