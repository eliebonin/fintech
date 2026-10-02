import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,get:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=initial;return [h.slots[i],(v:any)=>{h.slots[i]=v;}];},useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];}}));
vi.mock('@/lib/browser-api-client',()=>({bffGet:h.get}));
import {FutureFamilySelector} from './future-family-selector';
function find(node:any,p:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(p(node))return node;for(const c of [node.props?.children].flat(Infinity)){const f=find(c,p);if(f)return f;}}
const family={familyId:'family',familyNodeId:'node',familyCode:'ROOT',canonicalName:'Index future family',underlyingId:'index',underlyingName:'Index',contractCurrencyId:'usd',currency:'USD'};
function render(onSelect=vi.fn()){h.cursor=0;return FutureFamilySelector({onSelect});}
afterEach(()=>{h.slots=[];h.cursor=0;h.get.mockReset();});
it('selects the complete approved family without reconstructing its currency or underlying',async()=>{const select=vi.fn();h.get.mockResolvedValue({data:[family],meta:{total:1}});await find(render(select),n=>n.type==='button'&&n.props.children==='Find families').props.onClick();find(render(select),n=>n.type==='button'&&Array.isArray(n.props.children)).props.onClick();expect(select).toHaveBeenCalledWith(family);expect(h.get.mock.calls[0][0]).toContain('limit=20&offset=0');});
it('pages approved results instead of downloading every family',async()=>{h.get.mockResolvedValue({data:[family],meta:{total:21}});await find(render(),n=>n.type==='button'&&n.props.children==='Find families').props.onClick();await find(render(),n=>n.type==='button'&&n.props.children==='Next').props.onClick();expect(h.get.mock.calls[1][0]).toContain('offset=20');});
it('surfaces search errors without offering guessed families',async()=>{h.get.mockRejectedValue(new Error('Unavailable'));await find(render(),n=>n.type==='button'&&n.props.children==='Find families').props.onClick();expect(find(render(),n=>n.props?.role==='alert').props.children).toBe('Unavailable');});
