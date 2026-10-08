import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,send:vi.fn(),push:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return [h.slots[i],(value:any)=>h.slots[i]=typeof value==='function'?value(h.slots[i]):value];},useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},useEffect:()=>{}}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:h.push})}));
vi.mock('@/lib/browser-api-client',async original=>({...await original<typeof import('@/lib/browser-api-client')>(),submitBookedTradeFromBff:h.send}));
import {TradeTicket} from './trade-ticket';
import {BffApiError} from '@/lib/browser-api-client';
const listing={referenceNodeId:'listing',canonicalName:'Cash',parentReferenceNodeId:'instrument',status:'ACTIVE',isTradable:true,bookingEligible:true,tradingCurrency:'GBP',marketVenueMic:'XLON',venueName:'London',tradingSymbol:'DEMO'};
const correction={tradeId:'original',expectedSequenceNo:1,reason:'Wrong shares'};
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}}
function render(){h.cursor=0;return TradeTicket({listing,strategies:[{strategyId:'strategy',strategyCode:'TEST',displayName:'Test',status:'ACTIVE'}],context:{tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]},correction});}
afterEach(()=>{h.slots=[];h.cursor=0;h.send.mockReset();h.push.mockReset();vi.unstubAllGlobals();});
it('carries explicit replacement context through the cash review and submit',async()=>{
 let tree=render();for(const [id,value] of [['strategyId','strategy'],['quantity','10'],['executionPrice','1.23'],['tradeDatetime','2026-10-01T10:00:00Z'],['settlementDate','2026-10-05']])find(tree,n=>n.props?.id===id).props.onChange({target:{value}});
 find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 h.send.mockResolvedValueOnce({data:{trade:{tradeId:'replacement'}}});
 await find(render(),n=>n.type==='button'&&n.props.children==='Confirm booking').props.onClick();
 expect(h.send.mock.calls[0][0].correction).toEqual(correction);
});
it('offers a guarded history exit after a definitive conflict without resubmitting',async()=>{
 let tree=render();for(const [id,value] of [['strategyId','strategy'],['quantity','10'],['executionPrice','1.23'],['tradeDatetime','2026-10-01T10:00:00Z'],['settlementDate','2026-10-05']])find(tree,n=>n.props?.id===id).props.onChange({target:{value}});
 find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 h.send.mockRejectedValueOnce(new BffApiError(409,'Trade history changed','trade.sequence_conflict'));
 await find(render(),n=>n.type==='button'&&n.props.children==='Confirm booking').props.onClick();
 tree=render();expect(find(tree,n=>n.type==='button'&&n.props.children==='Confirm booking').props.disabled).toBe(true);
 expect(find(tree,n=>n.type==='a'&&n.props.href==='/trades').props.target).toBe('_blank');
 const exit=find(tree,n=>n.type==='button'&&n.props.children==='Leave blocked ticket');expect(exit).toBeDefined();
 expect(exit.props.disabled).toBe(true);
 const assign=vi.fn();vi.stubGlobal('window',{location:{assign}});
 exit.props.onClick();expect(assign).not.toHaveBeenCalled();expect(h.push).not.toHaveBeenCalled();
 const acknowledgement=find(tree,n=>n.type==='input'&&n.props.type==='checkbox'&&n.props['aria-label']==='I checked trade history and confirmed the booking result');expect(acknowledgement).toBeDefined();
 acknowledgement.props.onChange({target:{checked:true}});
 expect(find(render(),n=>n.type==='button'&&n.props.children==='Leave blocked ticket').props.disabled).toBe(false);
 find(render(),n=>n.type==='button'&&n.props.children==='Leave blocked ticket').props.onClick();
 expect(assign).toHaveBeenCalledWith('/trades');expect(h.push).not.toHaveBeenCalled();expect(h.send).toHaveBeenCalledOnce();
});
