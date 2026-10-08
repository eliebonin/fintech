import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
const h=vi.hoisted(()=>({detail:vi.fn()}));
vi.mock('next/navigation',()=>({redirect:(path:string)=>{throw new Error(`redirect:${path}`);},notFound:()=>{throw new Error('not-found');},useRouter:()=>({})}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:async()=>({tenantId:'tenant',userAccountId:'actor'}),getActiveTenantWorkspace:async()=>({membershipRole:'TENANT_ADMIN',moduleCodes:['TRADING'],tenantName:'Demo'})}));
vi.mock('@/lib/reference-api-client',()=>({getTradeBookingContext:async()=>({data:{tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]}}),getCashBookingListing:vi.fn()}));
vi.mock('@/lib/mvp-api-client',()=>({getBookedTradeDetail:h.detail,MvpApiError:class extends Error{status=404;}}));
import Page from './page';
import {CorrectionBookingGate} from '../record-correction-controls';
import {TradeTicket} from './trade-ticket';
const id='00000000-0000-7000-8000-000000000001';
const detail={trade:{tradeId:id,strategyId:'original-strategy',lifecycleStatus:'BOOKED',tradeType:'INVESTMENT'},lifecycleEvents:[{sequenceNo:1,eventType:'BOOKED',eventPayload:JSON.stringify({schemaVersion:1,kind:'CASH_BOOKING'})}]};
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}}
afterEach(()=>{h.detail.mockReset();vi.unstubAllGlobals();});
it('loads the tenant-owned original and gates a same-strategy replacement ticket',async()=>{
 h.detail.mockResolvedValueOnce({data:detail});vi.stubGlobal('fetch',async()=>Response.json({data:[{strategyId:'original-strategy',status:'ACTIVE'},{strategyId:'other',status:'ACTIVE'}]}));
 const tree=await Page({searchParams:Promise.resolve({corrects:id})});
 const gate=find(tree,n=>n.type===CorrectionBookingGate);expect(gate.props.original).toEqual(detail);
 expect(gate.props.strategies.map((s:any)=>s.strategyId)).toEqual(['original-strategy']);
 expect(gate.props.children).toBeUndefined();
 expect(gate.props.context.tenantId).toBe('tenant');
 expect(find(tree,n=>n.props?.['aria-label']==='Booking product')).toBeUndefined();
});
it('refuses unsupported originals rather than opening a normal unlinked ticket',async()=>{
 h.detail.mockResolvedValueOnce({data:{...detail,trade:{...detail.trade,lifecycleStatus:'CANCELLED'}}});
 await expect(Page({searchParams:Promise.resolve({corrects:id})})).rejects.toThrow(`redirect:/trades/${id}`);
});
it('does not fall back to an ordinary ticket when the original service fails',async()=>{
 h.detail.mockRejectedValueOnce(new Error('Unavailable'));
 const tree=await Page({searchParams:Promise.resolve({corrects:id})});
 expect(find(tree,n=>n.type===TradeTicket)).toBeUndefined();
 expect(find(tree,n=>n.props?.role==='alert').props.children).toContain('original booking could not be loaded');
});
it('returns opaque not-found when the original belongs to another tenant',async()=>{
 const {MvpApiError}=await import('@/lib/mvp-api-client');
 h.detail.mockRejectedValueOnce(new MvpApiError(404,'Not found'));
 await expect(Page({searchParams:Promise.resolve({corrects:id})})).rejects.toThrow('not-found');
});
