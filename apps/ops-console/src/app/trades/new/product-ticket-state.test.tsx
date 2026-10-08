import {afterEach,beforeEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({slots:[] as any[],cursor:0,effects:[] as (()=>void)[],send:vi.fn(),get:vi.fn(),push:vi.fn()}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:any)=>{const slots=h.slots,i=h.cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return [slots[i],(value:any)=>{slots[i]=typeof value==='function'?value(slots[i]):value;}];},useRef:(initial:any)=>{const i=h.cursor++;if(!(i in h.slots))h.slots[i]={current:initial};return h.slots[i];},useEffect:(setup:()=>void|(()=>void),deps?:unknown[])=>{const slots=h.slots,i=h.cursor++,previous=slots[i];if(previous&&deps&&deps.every((value,index)=>Object.is(value,previous.deps?.[index])))return;const effect={effect:true,setup,deps,cleanup:undefined as undefined|(()=>void)};slots[i]=effect;h.effects.push(()=>{previous?.cleanup?.();effect.cleanup=setup()||undefined;});}}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:h.push,refresh:vi.fn()})}));
vi.mock('@/lib/browser-api-client',async original=>({...await original<typeof import('@/lib/browser-api-client')>(),bffPost:h.send,bffGet:h.get}));
import {ProductTicket} from './product-ticket';
import {BookingSearchResults,ReadinessResults} from './booking-search-results';
import {PropertyFields} from './property-fields';
import {BffApiError} from '@/lib/api-errors';
import {PartyFields} from './party-fields';
import {ProductReview} from './product-ticket';
import type {ProductTerms} from './product-ticket-model';
const terms={instrumentId:'future',listingId:'listing',name:'Future',kind:'FUTURE' as const,executionRoute:'LISTED' as const,bookingEligible:true,termsFingerprint:'a'.repeat(64),currency:'USD',convention:{kind:'FUTURE' as const,effectiveFrom:'2026-09-01',priceCurrencyId:'currency',sourceReference:'Exchange specification',quoteFactor:'1',quantityUnit:'CONTRACTS' as const,priceBasis:'INDEX_POINTS' as const,monetaryMultiplier:'5',tickSize:'.25',allowNegativePrice:false,lastTradingAtUtc:'2027-03-19T13:30:00Z',finalSettlementDate:'2027-03-19'}};
const context={tenantId:'tenant',bookedByUserAccountId:'actor',properties:[{definitionId:'zero',code:'ZERO',label:'Numeric',description:null,valueType:'DECIMAL' as const,required:false,choices:[]}],tags:[]};
let correction:import('@/lib/trade-correction-model').BookingCorrection|undefined;
function render(kind:'FUTURE'|'SWAP'|'BOND'|'STRUCTURED_PRODUCT'='FUTURE',tenantId=context.tenantId){h.cursor=0;const tree=ProductTicket({kind,strategies:[{strategyId:'strategy',strategyCode:'TEST',displayName:'Test',status:'ACTIVE'}],context:{...context,tenantId},correction});h.effects.splice(0).forEach(effect=>effect());return tree;}
function unmount(){h.slots.filter(slot=>slot?.effect).forEach(effect=>effect.cleanup?.());h.slots=[];h.cursor=0;h.effects=[];}
function replayEffects(){const effects=h.slots.filter(slot=>slot?.effect);effects.forEach(effect=>effect.cleanup?.());effects.forEach(effect=>{effect.cleanup=effect.setup()||undefined;});}
function find(node:any,predicate:(n:any)=>boolean):any{if(!node||typeof node!=='object')return;if(predicate(node))return node;if(node.type===BookingSearchResults)return find(ReadinessResults({...node.props,showUnavailable:false,onShowUnavailable(){}}),predicate);for(const child of [node.props?.children].flat(Infinity)){const found=find(child,predicate);if(found)return found;}}
const button=(tree:any,text:string)=>find(tree,n=>n.type==='button'&&n.props.children===text),byId=(tree:any,id:string)=>find(tree,n=>n.props?.id===id);
async function selected(){h.get.mockResolvedValueOnce({data:[terms],meta:{total:1}}).mockResolvedValueOnce({data:terms});let tree=render();find(tree,n=>n.props?.['aria-label']==='Search products').props.onChange({target:{value:'Future'}});tree=render();await find(tree,n=>n.type==='form').props.onSubmit({preventDefault(){}});await button(render(),'Select product').props.onClick();return render();}
async function reviewed(){let tree=await selected();for(const [id,value] of [['strategyId','strategy'],['quantity','2'],['executionPrice','6000'],['tradeDatetime','2026-10-01T10:00:00Z'],['positionEffect','CLOSE']])byId(tree,id).props.onChange({target:{value}});find(tree,n=>n.type===PropertyFields).props.onChange({properties:{zero:'0'}});tree=render();find(tree,n=>n.type==='form').props.onSubmit({preventDefault(){}});return render();}
beforeEach(()=>{vi.stubGlobal('window',{location:{href:'http://test/trades/new'},history:{state:{}},addEventListener:vi.fn(),removeEventListener:vi.fn()});vi.stubGlobal('document',{addEventListener:vi.fn(),removeEventListener:vi.fn()});});
afterEach(()=>{correction=undefined;unmount();h.send.mockReset();h.get.mockReset();h.push.mockReset();vi.unstubAllGlobals();});
it.each(['FUTURE','SWAP','BOND','STRUCTURED_PRODUCT'] as const)('lets %s search and select references at an explicit historical date',async kind=>{
 const tree=render(kind),date=find(tree,n=>n.props?.['aria-label']==='Search date (UTC)');
 expect(date,'historical date must be editable before choosing the instrument').toBeDefined();
 date.props.onChange({target:{value:'2026-09-30'}});
 find(render(kind),n=>n.props?.['aria-label']==='Search products').props.onChange({target:{value:'Synthetic'}});
 h.get.mockResolvedValueOnce({data:[terms],meta:{total:1,offset:0,limit:25}}).mockResolvedValueOnce({data:terms});
 await find(render(kind),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 expect(new URL(h.get.mock.calls[0][0],'http://test').searchParams.get('asOfDate')).toBe('2026-09-30');
 await button(render(kind),'Select product').props.onClick();
 expect(new URL(h.get.mock.calls[1][0],'http://test').searchParams.get('asOfDate')).toBe('2026-09-30');
});
it('submits the confirmed correction context with the product ticket',async()=>{correction={tradeId:'original',expectedSequenceNo:1,reason:'Wrong count'};h.send.mockResolvedValueOnce({data:{trade:{tradeId:'replacement'}}});await button(await reviewed(),'Confirm booking').props.onClick();expect(h.send.mock.calls[0][1].correction).toEqual(correction);});
it('does not expose a cash settlement input for futures',async()=>expect(byId(await selected(),'settlementDate')).toBeUndefined());
it('preserves annotations and intent on review/edit',async()=>{button(await reviewed(),'Back to edit').props.onClick();const tree=render();expect(byId(tree,'positionEffect').props.value).toBe('CLOSE');expect(find(tree,n=>n.type===PropertyFields).props.draft.properties.zero).toBe('0');});
it('freezes request, tenant and key for an uncertain retry',async()=>{h.send.mockRejectedValueOnce(new BffApiError(503,'Unavailable')).mockResolvedValueOnce({data:{trade:{tradeId:'saved'}}});await button(await reviewed(),'Confirm booking').props.onClick();const tree=render();expect(button(tree,'Back to edit').props.disabled).toBe(true);await button(tree,'Retry unchanged booking').props.onClick();expect(h.send.mock.calls[1]).toEqual(h.send.mock.calls[0]);expect(h.send.mock.calls[0][1].settlementDate).toBeNull();expect(h.send.mock.calls[0][1].properties).toEqual([{definitionId:'zero',value:'0'}]);expect(h.push).toHaveBeenCalledWith('/trades/saved');});
it('prevents double submission',async()=>{let done:(x:any)=>void=()=>{};h.send.mockImplementation(()=>new Promise(resolve=>done=resolve));const confirm=button(await reviewed(),'Confirm booking');const first=confirm.props.onClick();await confirm.props.onClick();expect(h.send).toHaveBeenCalledOnce();done({data:{trade:{tradeId:'saved'}}});await first;});
it('blocks a stale snapshot rather than creating another trade',async()=>{h.send.mockRejectedValueOnce(new BffApiError(409,'Terms changed','product.terms_changed'));await button(await reviewed(),'Confirm booking').props.onClick();const tree=render();expect(button(tree,'Confirm booking').props.disabled).toBe(true);await button(tree,'Confirm booking').props.onClick();expect(h.send).toHaveBeenCalledOnce();});

const swap:ProductTerms={instrumentId:'swap',name:'Equity swap',kind:'SWAP',executionRoute:'OTC',bookingEligible:true,termsFingerprint:'b'.repeat(64),currency:'GBP',maturityDate:'2029-10-01',convention:{kind:'SWAP',effectiveFrom:'2026-09-01',priceCurrencyId:'gbp',sourceReference:'Confirmation',quoteFactor:'100',quantityUnit:'NOMINAL',priceBasis:'SWAP_VALUE_PER_NOTIONAL',quantityMinimum:'1E-12',quantityIncrement:'1E-12',otcAllowed:true},swapDetails:{performanceReferenceId:'equity',performanceReferenceName:'Equity',performanceDirection:'RECEIVE',returnProfileCode:'TOTAL',effectiveDate:'2026-09-01',sourceFacts:{},genericTerms:{schemaVersion:1,contractualNotional:'1000000.123456',notionalCurrencyId:'gbp',effectiveDate:'2026-09-01',maturityDate:'2029-10-01',performanceDirection:'RECEIVE',performanceReferenceId:'equity',returnBasis:'TOTAL',returnProfileId:'total',leverage:'2',financingTreatment:'NONE',performanceResetFrequency:'AT_MATURITY',redemptionRule:'TERMINATE',quoteCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Confirmation',additionalFundingAcknowledged:false}}};
async function selectedSwap(candidate=swap){h.get.mockResolvedValueOnce({data:[candidate],meta:{total:1}}).mockResolvedValueOnce({data:candidate});let tree=render('SWAP');find(tree,n=>n.props?.['aria-label']==='Search products').props.onChange({target:{value:'swap'}});await find(render('SWAP'),n=>n.type==='form').props.onSubmit({preventDefault(){}});await button(render('SWAP'),'Select product').props.onClick();return render('SWAP');}
it('prefills exact contractual nominal on selection and retains edits on ordinary rerender',async()=>{
 const tree=await selectedSwap();expect(byId(tree,'quantity').props.value).toBe('1000000.123456');byId(tree,'quantity').props.onChange({target:{value:'400000'}});
 expect(byId(render('SWAP'),'quantity').props.value).toBe('400000');expect(swap.swapDetails!.genericTerms!.contractualNotional).toBe('1000000.123456');
});
it('reviews and submits a serialized tiny contractual nominal prefill exactly',async()=>{
 const candidate={...swap,swapDetails:{...swap.swapDetails!,genericTerms:{...swap.swapDetails!.genericTerms!,contractualNotional:'1E-12'}}};
 const tree=await selectedSwap(candidate);expect(byId(tree,'quantity').props.value).toBe('1E-12');
 for(const [id,value] of [['strategyId','strategy'],['executionPrice','0'],['tradeDatetime','2026-10-01T10:00:00Z']])byId(tree,id).props.onChange({target:{value}});
 find(tree,n=>n.type===PartyFields).props.onChange({counterpartyOrganisationId:'bank'});find(render('SWAP'),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 const review=find(render('SWAP'),n=>n.type===ProductReview);expect(review).toBeDefined();expect(review.props.draft.quantity).toBe('1E-12');
 h.send.mockResolvedValue({data:{trade:{tradeId:'tiny'}}});await button(render('SWAP'),'Confirm booking').props.onClick();expect(h.send.mock.calls[0][1].quantity).toBe('1E-12');
});
it('retains partial nominal and annotations through review/back/edit and submits the edited quantity',async()=>{
 let tree=await selectedSwap();for(const [id,value] of [['strategyId','strategy'],['quantity','400000'],['executionPrice','2'],['tradeDatetime','2026-10-01T10:00:00Z']])byId(tree,id).props.onChange({target:{value}});
 find(tree,n=>n.type===PartyFields).props.onChange({counterpartyOrganisationId:'bank',counterpartyName:'Bank'});find(tree,n=>n.type===PropertyFields).props.onChange({properties:{zero:'0'},tagIds:[],externalReferences:[{referenceType:'CLIENT_REFERENCE',referenceValue:'source-1'}]});
 find(render('SWAP'),n=>n.type==='form').props.onSubmit({preventDefault(){}});tree=render('SWAP');expect(find(tree,n=>n.type===ProductReview),'wire-real nominal reaches review').toBeDefined();expect(find(tree,n=>n.type===ProductReview).props.draft.quantity).toBe('400000');button(tree,'Back to edit').props.onClick();tree=render('SWAP');expect(byId(tree,'quantity').props.value).toBe('400000');
 byId(tree,'quantity').props.onChange({target:{value:'200000'}});find(render('SWAP'),n=>n.type==='form').props.onSubmit({preventDefault(){}});h.send.mockResolvedValue({data:{trade:{tradeId:'saved'}}});await button(render('SWAP'),'Confirm booking').props.onClick();
 expect(h.send.mock.calls[0][0]).toBe('/api/trades/swaps');expect(h.send.mock.calls[0][1]).toMatchObject({quantity:'200000',properties:[{definitionId:'zero',value:'0'}],externalReferences:[{referenceType:'CLIENT_REFERENCE',referenceValue:'source-1',sourceSystemId:null}],expectedTermsFingerprint:'b'.repeat(64)});
});
it('clears stale annotations and quote on changing instruments and initializes the new nominal',async()=>{
 let tree=await selectedSwap();byId(tree,'quantity').props.onChange({target:{value:'400000'}});byId(tree,'executionPrice').props.onChange({target:{value:'2'}});find(tree,n=>n.type===PropertyFields).props.onChange({properties:{zero:'0'}});button(render('SWAP'),'Change product').props.onClick();
 tree=await selectedSwap({...swap,instrumentId:'other-swap',swapDetails:{...swap.swapDetails!,genericTerms:{...swap.swapDetails!.genericTerms!,contractualNotional:'700000'}}});expect(byId(tree,'quantity').props.value).toBe('700000');expect(byId(tree,'executionPrice').props.value).toBe('');expect(find(tree,n=>n.type===PropertyFields).props.draft.properties).toEqual({});
});
it('clears instrument and tenant-specific draft when tenant context changes',async()=>{
 const tree=await selectedSwap();byId(tree,'executionPrice').props.onChange({target:{value:'2'}});render('SWAP','other');expect(byId(render('SWAP','other'),'executionPrice')).toBeUndefined();expect(button(render('SWAP','other'),'Search products')).toBeDefined();
});
it('does not navigate to an old booking after switching tenants away and back',async()=>{
 let tree=await selectedSwap();for(const [id,value] of [['strategyId','strategy'],['executionPrice','2'],['tradeDatetime','2026-10-01T10:00:00Z']])byId(tree,id).props.onChange({target:{value}});find(tree,n=>n.type===PartyFields).props.onChange({counterpartyOrganisationId:'bank'});find(render('SWAP'),n=>n.type==='form').props.onSubmit({preventDefault(){}});
 let done:(value:any)=>void=()=>{};h.send.mockImplementation(()=>new Promise(resolve=>done=resolve));const confirm=button(render('SWAP'),'Confirm booking');expect(confirm,'wire-real nominal reaches confirmation').toBeDefined();const pending=confirm.props.onClick();render('SWAP','other');render('SWAP','tenant');done({data:{trade:{tradeId:'old-tenant-booking'}}});await pending;expect(h.push).not.toHaveBeenCalled();
});
it('ignores an old confirmation after keyed unmount and a new tenant ticket mounts',async()=>{
 let done:(value:any)=>void=()=>{};h.send.mockImplementation(()=>new Promise(resolve=>done=resolve));const pending=button(await reviewed(),'Confirm booking').props.onClick();unmount();render('FUTURE','other');done({data:{trade:{tradeId:'old-booking'}}});await pending;expect(h.push).not.toHaveBeenCalled();expect(button(render('FUTURE','other'),'Search products')).toBeDefined();
});
it('ignores an old confirmation after unmount and returning in a fresh instance of the same tenant',async()=>{
 let done:(value:any)=>void=()=>{};h.send.mockImplementation(()=>new Promise(resolve=>done=resolve));const pending=button(await reviewed(),'Confirm booking').props.onClick();unmount();render('FUTURE','other');unmount();render();done({data:{trade:{tradeId:'old-booking'}}});await pending;expect(h.push).not.toHaveBeenCalled();
});
it('keeps current-instance confirmation and unchanged retries valid after strict effect replay',async()=>{
 const tree=await reviewed();replayEffects();h.send.mockRejectedValueOnce(new BffApiError(503,'Unavailable')).mockResolvedValueOnce({data:{trade:{tradeId:'current-booking'}}});await button(tree,'Confirm booking').props.onClick();await button(render(),'Retry unchanged booking').props.onClick();expect(h.send.mock.calls[1]).toEqual(h.send.mock.calls[0]);expect(h.push).toHaveBeenCalledWith('/trades/current-booking');
});
