import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,search:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return [h.slots[i],(value:any)=>h.slots[i]=typeof value==='function'?value(h.slots[i]):value];},useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},useEffect:()=>{}}));
vi.mock('next/navigation',()=>({useRouter:()=>({})}));
vi.mock('@/lib/browser-api-client',async original=>({...await original<typeof import('@/lib/browser-api-client')>(),searchOptionBookingListingsFromBff:h.search,searchFxForwardBookingInstrumentsFromBff:h.search}));
import {OptionTicket} from './option-ticket';
import {FxForwardTicket} from './fx-forward-ticket';
function find(node:any,test:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(test(node))return node;for(const child of [node.props?.children].flat(Infinity)){const found=find(child,test);if(found)return found;}}
const context={tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]};
afterEach(()=>{h.slots=[];h.cursor=0;h.search.mockReset();});
it.each(['OPTION','FX_FORWARD'])('uses the selected UTC search date for %s and resets pagination on date change',async(kind)=>{
 const render=()=>{h.cursor=0;return (kind==='OPTION'?OptionTicket:FxForwardTicket)({strategies:[],context});};
 let tree=render();find(tree,n=>n.props?.type==='date').props.onChange({target:{value:'2026-09-30'}});find(tree,n=>n.props?.['aria-label']?.startsWith('Search')).props.onChange({target:{value:'Test'}});
 h.search.mockResolvedValueOnce({data:[],meta:{offset:0,limit:25,total:0}});await find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 expect(h.search.mock.calls[0][3]).toBe('2026-09-30');expect(h.search.mock.calls[0][2]).toBe(0);
});
