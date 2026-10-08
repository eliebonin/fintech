import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,search:vi.fn(),detail:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
  useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return [h.slots[i],(value:any)=>h.slots[i]=typeof value==='function'?value(h.slots[i]):value];},
  useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},useEffect:()=>{}}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn()})}));
vi.mock('@/lib/browser-api-client',async original=>({...await original<typeof import('@/lib/browser-api-client')>(),searchCashBookingListingsFromBff:h.search,getCashBookingListingFromBff:h.detail}));
import {TradeTicket} from './trade-ticket';
import {BookingSearchResults} from './booking-search-results';
const ready={referenceNodeId:'listing',parentReferenceNodeId:'instrument',canonicalName:'Cash listing',status:'ACTIVE',isTradable:true,bookingEligible:true,readinessStatus:'READY',marketVenueMic:'XLON',venueName:'London',tradingSymbol:'TEST',tradingCurrency:'GBP'};
function render(){h.cursor=0;return TradeTicket({strategies:[],context:{tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]}});}
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}}
const results=()=>find(render(),n=>n.type===BookingSearchResults).props;
function query(value:string){find(render(),n=>n.props?.['aria-label']==='Search active listings').props.onChange({target:{value}});}
const search=()=>find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
afterEach(()=>{h.slots=[];h.cursor=0;h.search.mockReset();h.detail.mockReset();});
it('ignores a late search response after the query changes',async()=>{
  let finish:(v:any)=>void=()=>{};h.search.mockImplementation(()=>new Promise(resolve=>finish=resolve));
  query('old');const pending=search();query('new');finish({data:[ready],meta:{total:1}});await pending;
  expect(results().items).toEqual([]);expect(results().searched).toBe(false);expect(results().loading).toBe(false);
});
it('refreshes selection and keeps newly unavailable listings out of execution',async()=>{
  h.search.mockResolvedValue({data:[ready],meta:{total:1}});query('cash');await search();
  h.detail.mockResolvedValue({data:{...ready,bookingEligible:false,readinessStatus:'INACTIVE',ineligibilityMessage:'Listing has been suspended.'}});
  await results().onSelect('listing');await Promise.resolve();
  expect(results().items[0].bookingEligible).toBe(false);
  expect(find(render(),n=>n.type==='button'&&n.props.children==='Review booking')).toBeUndefined();
  expect(find(render(),n=>n.props?.role==='alert').props.children).toBe('Listing has been suspended.');
});
it('does not open execution when selection revalidation is unavailable',async()=>{
  h.search.mockResolvedValue({data:[ready],meta:{total:1}});query('cash');await search();
  h.detail.mockRejectedValue(new Error('Readiness service unavailable.'));await results().onSelect('listing');await Promise.resolve();
  expect(find(render(),n=>n.type==='button'&&n.props.children==='Review booking')).toBeUndefined();
  expect(find(render(),n=>n.props?.role==='alert').props.children).toBe('Readiness service unavailable.');
});
it('advances the raw offset even when a whole page is omitted after scope changes',async()=>{
  h.search.mockResolvedValueOnce({data:[],meta:{offset:0,limit:25,total:50}}).mockResolvedValueOnce({data:[],meta:{offset:25,limit:25,total:50}});
  query('cash');await search();expect(results().hasMore).toBe(true);await results().onLoadMore();await Promise.resolve();
  expect(h.search.mock.calls[1][2]).toBe(25);expect(results().hasMore).toBe(false);
});
it('invalidates search results when the readiness date changes',async()=>{
  h.search.mockResolvedValue({data:[ready],meta:{total:1}});query('cash');await search();
  find(render(),n=>n.props?.['aria-label']==='Cash readiness date').props.onChange({target:{value:'2026-09-30'}});
  expect(results().items).toEqual([]);expect(results().searched).toBe(false);await search();
  expect(h.search.mock.calls[1][1]).toBe('2026-09-30');
});
