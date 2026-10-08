import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],effects:[] as (()=>any)[],cursor:0,send:vi.fn(),refresh:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return [h.slots[i],(value:any)=>h.slots[i]=typeof value==='function'?value(h.slots[i]):value];},useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},useEffect:(callback:()=>any)=>{h.effects.push(callback);}}));
vi.mock('next/navigation',()=>({useRouter:()=>({refresh:h.refresh})}));
vi.mock('@/lib/browser-api-client',async original=>({...await original<typeof import('@/lib/browser-api-client')>(),cancelBookingRecordFromBff:h.send}));
import {RecordCorrectionActions,CorrectionBookingGate} from './record-correction-controls';
import {BffApiError} from '@/lib/api-errors';
import type {TradeDetailPayload} from '@/lib/trades';
import {TradeTicket} from './new/trade-ticket';
import {FxForwardTicket} from './new/fx-forward-ticket';
import {OptionTicket} from './new/option-ticket';
import {ProductTicket} from './new/product-ticket';
const detail={trade:{tradeId:'00000000-0000-7000-8000-000000000001',lifecycleStatus:'BOOKED',tradeType:'INVESTMENT',strategyId:'strategy',strategyName:'Demo strategy',subjectName:'Demo security',quantity:'10',quantityUnit:'SHARES',executionPrice:'1.23',tradeDatetimeUtc:'2026-10-01T10:00:00Z'},lifecycleEvents:[{sequenceNo:1,eventType:'BOOKED',eventPayload:JSON.stringify({schemaVersion:1,kind:'CASH_BOOKING'})}]} as TradeDetailPayload['data'];
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}}
const button=(tree:any,label:string)=>find(tree,n=>n.type==='button'&&n.props.children===label);
function render(){h.cursor=0;return RecordCorrectionActions({detail,tenantId:'tenant'});}
function reviewed(){button(render(),'Cancel erroneous booking').props.onClick();find(render(),n=>n.type==='textarea').props.onChange({target:{value:'Wrong security'}});find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});return render();}
afterEach(()=>{h.slots=[];h.effects=[];h.cursor=0;h.send.mockReset();h.refresh.mockReset();vi.unstubAllGlobals();});
it('prevents native reason-form submission until client handlers are mounted',()=>{
 const gate=()=>{h.cursor=0;return CorrectionBookingGate({original:detail,strategies:[],context:{tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]}});};
 expect(button(gate(),'Continue to replacement ticket').props.disabled).toBe(true);
 expect(find(gate(),n=>n.type==='textarea').props.disabled).toBe(true);
 h.effects.at(-1)!();
 expect(button(gate(),'Continue to replacement ticket').props.disabled).toBe(false);
 expect(find(gate(),n=>n.type==='textarea').props.disabled).toBe(false);
});
it('requires reason/review and does not cancel on the first action',()=>{
 button(render(),'Cancel erroneous booking').props.onClick();find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 expect(button(render(),'Confirm record cancellation')).toBeUndefined();expect(h.send).not.toHaveBeenCalled();
});
it('retains the original cancellation envelope across uncertain retry',async()=>{
 h.send.mockRejectedValueOnce(new BffApiError(503,'Unavailable')).mockResolvedValueOnce({data:detail});
 await button(reviewed(),'Confirm record cancellation').props.onClick();
 expect(button(render(),'Back to reason').props.disabled).toBe(true);
 await button(render(),'Retry unchanged cancellation').props.onClick();
 expect(h.send.mock.calls[1]).toEqual(h.send.mock.calls[0]);expect(h.send.mock.calls[0][1]).toEqual({expectedSequenceNo:1,reason:'Wrong security'});expect(h.send.mock.calls[0][3]).toBe('tenant');expect(h.refresh).toHaveBeenCalledOnce();
});
it('blocks sequence conflicts rather than minting another cancellation',async()=>{
 h.send.mockRejectedValueOnce(new BffApiError(409,'History changed','trade.correction_conflict'));
 await button(reviewed(),'Confirm record cancellation').props.onClick();
 expect(button(render(),'Confirm record cancellation').props.disabled).toBe(true);
 await button(render(),'Confirm record cancellation').props.onClick();expect(h.send).toHaveBeenCalledOnce();
});
it.each(['CASH','FX_FORWARD','OPTION','STRUCTURED_PRODUCT','FUTURE','BOND','SWAP'] as const)('constructs a real %s replacement ticket from serializable data after the reason gate',product=>{
 const original={...detail,lifecycleEvents:[{sequenceNo:1,eventType:'BOOKED',eventPayload:JSON.stringify({schemaVersion:1,kind:product==='CASH'?'CASH_BOOKING':product==='FX_FORWARD'?'FX_FORWARD_BOOKING':product==='OPTION'?'OPTION_BOOKING':'PRODUCT_BOOKING',economics:{terms:{kind:product}}})}]} as TradeDetailPayload['data'];
 const strategies=[{strategyId:'strategy',strategyCode:'DEMO',displayName:'Demo',status:'ACTIVE'}];
 const context={tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]};
 const gate=()=>{h.cursor=0;return CorrectionBookingGate({original,strategies,context});};
 const component=product==='CASH'?TradeTicket:product==='FX_FORWARD'?FxForwardTicket:product==='OPTION'?OptionTicket:ProductTicket;
 expect(find(gate(),n=>n.type===component)).toBeUndefined();
 find(gate(),n=>n.type==='textarea').props.onChange({target:{value:'Correct quantity'}});
 find(gate(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 const ticket=find(gate(),n=>n.type===component);
 expect(ticket?.props.correction).toEqual({tradeId:detail.trade.tradeId,expectedSequenceNo:1,reason:'Correct quantity'});
 expect(ticket.props.strategies).toEqual(strategies);expect(ticket.props.context).toEqual(context);
 if(component===ProductTicket)expect(ticket.props.kind).toBe(product);
});
it('guards browser back while cancellation outcome is uncertain',async()=>{
 h.send.mockRejectedValueOnce(new BffApiError(503,'Unavailable'));
 await button(reviewed(),'Confirm record cancellation').props.onClick();render();
 const handlers:Record<string,any>={},pushState=vi.fn(),stop=vi.fn();
 vi.stubGlobal('window',{location:{href:'http://test/trades/original'},history:{state:{route:'detail'},pushState},alert:vi.fn(),addEventListener:(name:string,handler:any)=>handlers[name]=handler,removeEventListener:vi.fn()});
 vi.stubGlobal('document',{addEventListener:vi.fn(),removeEventListener:vi.fn()});
 const cleanup=h.effects.at(-1)!();
 expect(handlers.popstate).toBeTypeOf('function');handlers.popstate({stopImmediatePropagation:stop});
 expect(stop).toHaveBeenCalledOnce();expect(pushState).toHaveBeenCalledWith({route:'detail'},'','http://test/trades/original');cleanup();
});
