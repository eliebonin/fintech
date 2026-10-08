import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,effects:[] as (()=>void)[],get:vi.fn(),send:vi.fn(),search:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),
  useState:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return [h.slots[i],(v:any)=>{h.slots[i]=typeof v==='function'?v(h.slots[i]):v;}];},
  useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},
  useEffect:(callback:()=>void)=>{const i=h.cursor++;if(!(i in h.slots)){h.slots[i]=true;h.effects.push(callback);}}
}));
vi.mock('@/lib/browser-api-client',()=>({bffPost:h.send,bffGet:h.get,searchReferenceNodesFromBff:h.search}));
import {SwapCreationForm} from './swap-creation-form';
import {BffApiError} from '@/lib/api-errors';
function find(node:any,p:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(p(node))return node;for(const c of [node.props?.children].flat(Infinity)){const found=find(c,p);if(found)return found;}}
function all(node:any,p:(n:any)=>boolean):any[]{if(!node||typeof node!=='object')return [];return [...(p(node)?[node]:[]),...[node.props?.children].flat(Infinity).flatMap(c=>all(c,p))];}
function render(tenantId='tenant'){h.cursor=0;return SwapCreationForm({tenantId});}
function change(name:string,value:string){const node=find(render(),n=>n.props?.name===name);expect(node,`${name} input`).toBeDefined();node.props.onChange({target:{value,checked:value==='on'}});}
function button(text:string){return find(render(),n=>n.type==='button'&&[n.props.children].flat(Infinity).join('')===text);}
async function setup(dayCountUnavailable=false){
  h.get.mockImplementation(async(path:string)=>{if(dayCountUnavailable&&path.includes('day-count'))throw new Error('Day-count unavailable');return {data:path.includes('currencies')?[{items:[{currencyId:'gbp',currencyCode:'GBP',displayName:'Pound'}]}]:path.includes('return-profiles')?[
    {returnProfileId:'total',displayName:'Governed custom total',baseReturnBasis:'TOTAL',financingTreatment:'NONE',requiresFinancingReference:false},
    {returnProfileId:'excess',displayName:'Governed custom excess',baseReturnBasis:'TOTAL',financingTreatment:'SUBTRACT_REFERENCE_RATE',requiresFinancingReference:true},
    {returnProfileId:'price',displayName:'Price return',baseReturnBasis:'PRICE',financingTreatment:'NONE',requiresFinancingReference:false}
  ]:[{dayCountConventionId:'act365',displayName:'Actual / 365',conventionCode:'ACT_365'}]};});
  render();h.effects.splice(0).forEach(f=>f());await Promise.resolve();await Promise.resolve();
  h.search.mockResolvedValue({data:[{referenceNodeId:'ref',canonicalName:'Approved equity',nodeType:'INSTRUMENT',instrumentType:'EQUITY',status:'ACTIVE'},
    {referenceNodeId:'swap',canonicalName:'Recursive swap',nodeType:'INSTRUMENT',instrumentType:'SWAP',status:'ACTIVE'},
    {referenceNodeId:'old',canonicalName:'Retired',nodeType:'INDEX',status:'RETIRED'}]});
  change('performanceQuery','equity');await button('Search performance reference').props.onClick();button('Approved equity').props.onClick();
  for(const [name,value] of Object.entries({canonicalName:'Equity performance swap',tenantIdentifier:'SW-1',contractualNotional:'1000000.123456789012',notionalCurrencyId:'gbp',effectiveDate:'2026-10-03',maturityDate:'2027-10-03',performanceDirection:'RECEIVE',returnBasis:'TOTAL',returnProfileId:'total',performanceResetFrequency:'AT_MATURITY',redemptionRule:'TERMINATE',quoteFactor:'100',sourceReference:'Signed confirmation section 4'}))change(name,value);
}
function review(){find(render(),n=>n.type==='form').props.onSubmit({preventDefault(){}});}
async function submit(){h.send.mockResolvedValue({data:{proposalId:'pending-1'}});review();const submitButton=button('Submit swap for approval');expect(submitButton,'valid contract reaches review').toBeDefined();await submitButton.props.onClick();return h.send.mock.calls.at(-1)![1];}
async function funding(){change('includeFunding','on');h.search.mockResolvedValue({data:[{referenceNodeId:'sonia',canonicalName:'SONIA',nodeType:'RATE_INDEX',status:'ACTIVE'}]});change('fundingQuery','sonia');await button('Search funding reference').props.onClick();button('SONIA').props.onClick();for(const [name,value] of Object.entries({fundingSpreadBp:'150.1234',fundingNotionalBasis:'LEVERAGED_NOMINAL',dayCountConventionId:'act365',interestCalculationMethod:'Compounded overnight, confirmation section 5',fundingResetFrequency:'MONTHLY',fundingPaymentFrequency:'QUARTERLY'}))change(name,value);}
afterEach(()=>{h.slots=[];h.cursor=0;h.effects=[];h.get.mockReset();h.send.mockReset();h.search.mockReset();});
it.each([['contractualNotional','1000000000000000000'],['leverage','1000000000000000000'],['quoteFactor','1000000000000']])('rejects fixed-scale integer overflow for %s before review',async(name,value)=>{
  await setup();change(name,value);review();expect(button('Submit swap for approval')).toBeUndefined();
});
it('rejects fixed-scale funding spread integer overflow before review',async()=>{
  await setup();await funding();change('fundingSpreadBp','10000000000000000');review();expect(button('Submit swap for approval')).toBeUndefined();
});
it('has four form groups and uses tenant-visible economic reference lookup',async()=>{
  await setup();expect(all(render(),n=>n.type==='fieldset')).toHaveLength(4);
  expect(h.get).toHaveBeenCalledWith('/api/currencies?groups=REGULAR');
  expect(h.search).toHaveBeenCalledWith('equity',{nodeType:['INSTRUMENT','INDEX'],referenceLevel:'ECONOMIC'});
  expect(button('Recursive swap')).toBeUndefined();expect(button('Retired')).toBeUndefined();
  expect(find(render(),n=>n.props?.name==='fundingSpreadBp')).toBeUndefined();
  expect(find(render(),n=>n.type==='option'&&n.props.value==='price')).toBeUndefined();
});
it('reviews and edits without losing decimal strings, then creates only a pending request',async()=>{
  await setup();review();button('Back to edit').props.onClick();expect(find(render(),n=>n.props?.name==='contractualNotional').props.value).toBe('1000000.123456789012');
  const payload=await submit();expect(payload).toMatchObject({canonicalName:'Equity performance swap',tenantIdentifier:'SW-1',terms:{contractualNotional:'1000000.123456789012',leverage:'1',quoteFactor:'100',quoteCurrencyId:'gbp',financingTreatment:'NONE',fundingReferenceId:null}});
  expect(h.send.mock.calls[0][4]).toEqual({'X-Expected-Tenant-Id':'tenant'});
  expect(find(render(),n=>n.type==='h2').props.children).toBe('Swap request pending approval');
});
it('converts funding spread precisely and clears funding on off/on/off',async()=>{
  await setup();await funding();const payload=await submit();expect(payload.terms.fundingSpread).toBe('0.01501234');
  expect(h.search).toHaveBeenLastCalledWith('sonia',{nodeType:'RATE_INDEX',referenceLevel:'ECONOMIC'});
  h.slots=[];h.cursor=0;await setup();await funding();change('includeFunding','');change('includeFunding','on');expect(find(render(),n=>n.props?.name==='fundingSpreadBp').props.value).toBe('');change('includeFunding','');
  const clean=await submit();expect(clean.terms).toMatchObject({fundingReferenceId:null,fundingSpread:null,dayCountConventionId:null,fundingNotionalBasis:null,fundingResetFrequency:null,fundingPaymentFrequency:null,interestCalculationMethod:null});
});
it('requires source-backed custom, continuation and additional funding terms',async()=>{
  await setup();change('performanceResetFrequency','CUSTOM');review();expect(find(render(),n=>n.props?.role==='alert')).toBeDefined();expect(button('Submit swap for approval')).toBeUndefined();
  change('performanceScheduleDescription','Confirmation custom dates');change('redemptionRule','CONTINUE');review();expect(button('Submit swap for approval')).toBeUndefined();
  change('continuationDescription','Reinvest under confirmation section 6');await funding();change('returnBasis','EXCESS');change('returnProfileId','excess');review();expect(button('Submit swap for approval')).toBeUndefined();
  change('additionalFundingAcknowledged','on');change('additionalFundingEvidence','Confirmation explicitly charges additional funding');const payload=await submit();expect(payload.terms.financingTreatment).toBe('EMBEDDED_AND_SEPARATE');
});
it('shows upstream field errors while retaining an editable review',async()=>{
  await setup();review();h.send.mockRejectedValue(new BffApiError(422,'Terms invalid','VALIDATION_ERROR',undefined,{'terms.quoteFactor':['Source divisor required']}));await button('Submit swap for approval').props.onClick();
  expect(JSON.stringify(find(render(),n=>n.props?.role==='alert'))).toContain('Source divisor required');button('Back to edit').props.onClick();expect(find(render(),n=>n.props?.name==='quoteFactor').props.value).toBe('100');
});
it('retains an uncertain-response key across retries and replaces it after editing',async()=>{
  await setup();review();h.send.mockRejectedValue(new Error('Unknown write outcome'));
  await button('Submit swap for approval').props.onClick();
  const original=h.send.mock.calls[0][1].idempotencyKey;
  expect(original).toEqual(expect.any(String));
  await button('Submit swap for approval').props.onClick();
  expect(h.send.mock.calls[1][1].idempotencyKey).toBe(original);
  button('Back to edit').props.onClick();change('canonicalName','Edited intent');review();
  await button('Submit swap for approval').props.onClick();
  expect(h.send.mock.calls[2][1].idempotencyKey).not.toBe(original);
});
it('blocks stale forms when tenant props change',async()=>{
  await setup();review();render('other');const tree=render('other');expect(JSON.stringify(tree)).toContain('tenant changed');expect(find(tree,n=>n.type==='button'&&n.props.children==='Submit swap for approval')).toBeUndefined();expect(h.send).not.toHaveBeenCalled();
});
it('permits negative and zero funding spreads without float rounding',async()=>{
  await setup();await funding();change('fundingSpreadBp','-0.0001');expect((await submit()).terms.fundingSpread).toBe('-0.00000001');
  h.slots=[];h.cursor=0;await setup();await funding();change('fundingSpreadBp','0');expect((await submit()).terms.fundingSpread).toBe('0');
});
it('rejects funding precision exceeding the contract and incomplete funding conventions',async()=>{
  await setup();await funding();change('fundingSpreadBp','150.123456');review();expect(button('Submit swap for approval')).toBeUndefined();expect(JSON.stringify(find(render(),n=>n.props?.role==='alert'))).toContain('4 decimal places');
  change('fundingSpreadBp','150');change('interestCalculationMethod','');review();expect(button('Submit swap for approval')).toBeUndefined();
});
it('requires separate custom reset and payment sources and discards sources when frequency changes',async()=>{
  await setup();await funding();change('fundingResetFrequency','CUSTOM');change('fundingPaymentFrequency','CUSTOM');review();expect(button('Submit swap for approval')).toBeUndefined();
  change('fundingResetScheduleDescription','Reset confirmation schedule');change('fundingPaymentScheduleDescription','Payment confirmation schedule');review();button('Back to edit').props.onClick();change('fundingResetFrequency','MONTHLY');change('fundingPaymentFrequency','QUARTERLY');
  const payload=await submit();expect(payload.terms.fundingResetScheduleDescription).toBeNull();expect(payload.terms.fundingPaymentScheduleDescription).toBeNull();
});
it('does not require a funding-only day-count catalogue for a swap without funding',async()=>{
  await setup(true);expect((await submit()).terms.fundingReferenceId).toBeNull();
});
