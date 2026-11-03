import {afterEach,expect,it,vi} from 'vitest';
vi.mock('@/lib/use-retained-navigation',()=>({useRetainedNavigation:()=>{}}));
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,effects:[] as (()=>void)[],get:vi.fn(),send:vi.fn(),search:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
  useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return [h.slots[i],(v:any)=>{h.slots[i]=typeof v==='function'?v(h.slots[i]):v;}];},
  useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},
  useEffect:(callback:()=>void)=>{const i=h.cursor++;if(!(i in h.slots)){h.slots[i]=true;h.effects.push(callback);}}
}));
vi.mock('@/lib/browser-api-client',()=>({bffPost:h.send,bffGet:h.get,searchReferenceNodesFromBff:h.search}));
import {RateSwapCreationForm} from './rate-swap-creation-form';
function find(node:any,p:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(p(node))return node;for(const c of [node.props?.children].flat(Infinity)){const found=find(c,p);if(found)return found;}}
function render(tenantId='tenant'){h.cursor=0;return RateSwapCreationForm({tenantId});}
function change(name:string,value:string){const node=find(render(),n=>n.props?.name===name);expect(node,name).toBeDefined();node.props.onChange({target:{value}});}
function button(label:string){return find(render(),n=>n.type==='button'&&[n.props.children].flat(Infinity).join('')===label);}
async function setup(){
  h.get.mockImplementation(async(path:string)=>({data:path.includes('currencies')?[{items:[{currencyId:'gbp',currencyCode:'GBP'},{currencyId:'usd',currencyCode:'USD'}]}]:[{dayCountConventionId:'day',displayName:'Actual / 365'}]}));
  render();h.effects.splice(0).forEach(f=>f());await Promise.resolve();await Promise.resolve();
  for(const [prefix,label] of [['pay','SOFR'],['receive','SONIA']]){
    h.search.mockResolvedValue({data:[{referenceNodeId:prefix,canonicalName:label,nodeType:'RATE_INDEX',status:'ACTIVE'}]});
    change(`${prefix}RateQuery`,label);await button(`Search ${prefix} rate`).props.onClick();button(label).props.onClick();
  }
  for(const [name,value] of Object.entries({canonicalName:'Independent rate swap',contractualNotional:'26000000',notionalCurrencyId:'gbp',effectiveDate:'2026-10-01',maturityDate:'2027-10-01',quoteFactor:'1',sourceReference:'Signed confirmation',principalExchange:'NONE',
    payNotional:'34700000',payCurrencyId:'usd',paySpreadBp:'0',payDayCountConventionId:'day',payInterestCalculationMethod:'Compounded overnight',payObservationDescription:'Section 4',payResetFrequency:'QUARTERLY',payPaymentFrequency:'QUARTERLY',
    receiveNotional:'26000000',receiveCurrencyId:'gbp',receiveSpreadBp:'13.5',receiveDayCountConventionId:'day',receiveInterestCalculationMethod:'Compounded overnight',receiveObservationDescription:'Section 5',receiveResetFrequency:'QUARTERLY',receivePaymentFrequency:'QUARTERLY'}))change(name,value);
}
afterEach(()=>{h.slots=[];h.cursor=0;h.effects=[];vi.clearAllMocks();});
it('reviews and submits two independent rate legs using exact spreads and expected tenant',async()=>{
  await setup();find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
  h.send.mockResolvedValue({data:{proposalId:'rate-request'}});await button('Submit swap for approval').props.onClick();
  const call=h.send.mock.calls.at(-1)!,terms=call[1].terms;
  expect(terms.swapKind).toBe('RATE_EXCHANGE');expect(terms.legs[0]).toMatchObject({direction:'PAY',rateReferenceId:'pay',currencyId:'usd',contractualNotional:'34700000',spread:'0'});
  expect(terms.legs[1]).toMatchObject({direction:'RECEIVE',rateReferenceId:'receive',currencyId:'gbp',spread:'0.00135'});
  expect(terms).not.toHaveProperty('performanceReferenceId');expect(call[4]).toEqual({'X-Expected-Tenant-Id':'tenant'});
});
it('blocks a changed tenant before submitting',async()=>{
  await setup();const changed=render('other');expect(JSON.stringify(changed)).toContain('active tenant changed');expect(h.send).not.toHaveBeenCalled();
});
it('retains an uncertain submission and its key for unchanged retry',async()=>{
  await setup();find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});
  h.send.mockRejectedValueOnce(new Error('Connection lost'));await button('Submit swap for approval').props.onClick();
  expect(button('Edit terms').props.disabled).toBe(true);
  const first=h.send.mock.calls[0][1];h.send.mockResolvedValue({data:{proposalId:'confirmed'}});await button('Retry unchanged submission').props.onClick();
  expect(h.send.mock.calls[1][1]).toEqual(first);
});
