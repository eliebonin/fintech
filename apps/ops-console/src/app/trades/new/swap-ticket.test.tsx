import {describe,it,expect,vi} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn(),refresh:vi.fn()})}));
import {buildProductPayload,validateProductDraft,productAmount,type ProductTerms,type ProductDraft} from './product-ticket-model';
import {ProductFacts,ProductReview,ProductTicket} from './product-ticket';
it('labels absent optional funding explicitly in existing product facts',()=>{
  const markup=renderToStaticMarkup(<ProductFacts terms={{...terms,swapDetails:{...terms.swapDetails!,fundingReferenceId:null,fundingReferenceName:null,fundingSpread:null}}}/>);
  expect(markup).toContain('No separate funding leg');
  expect(markup).not.toContain('Canonical funding direction');expect(markup).not.toContain('Funding spread (decimal)');
});
import {ProductConventionForm} from '@/components/product-convention-form';
import type {TradeBookingContext} from '@/lib/browser-api-client';
import type {components} from 'api-contracts';
const generic:components['schemas']['GenericSwapTerms-Output']={schemaVersion:1,contractualNotional:'1000000',notionalCurrencyId:'gbp',effectiveDate:'2026-09-01',maturityDate:'2029-08-28',performanceDirection:'RECEIVE',performanceReferenceId:'equity',returnBasis:'TOTAL',returnProfileId:'total',leverage:'2',financingTreatment:'NONE',performanceResetFrequency:'CUSTOM',performanceScheduleDescription:'Confirmation reset schedule',redemptionRule:'CONTINUE',continuationDescription:'Reinvest proceeds under section 6',quoteCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Signed whole-swap confirmation',additionalFundingAcknowledged:false};
const terms:ProductTerms={instrumentId:'swap',name:'Autocall swap',kind:'SWAP',executionRoute:'OTC',currency:'GBP',maturityDate:'2029-08-28',bookingEligible:true,termsFingerprint:'a'.repeat(64),
 convention:{kind:'SWAP',effectiveFrom:'2026-09-01',priceCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Confirmation',quantityUnit:'NOMINAL',priceBasis:'SWAP_VALUE_PER_NOTIONAL',quantityMinimum:'1000',quantityIncrement:'1000',otcAllowed:true},
 swapDetails:{performanceReferenceId:'autocall',performanceReferenceName:'Autocall reference',performanceDirection:'RECEIVE',returnProfileCode:'GROSS_TOTAL_RETURN',fundingReferenceId:'rate',fundingReferenceName:'SONIA',fundingDirection:'PAY',fundingSpread:'0.01',effectiveDate:'2026-09-01',sourceFacts:{}}};
const draft:ProductDraft={strategyId:'s',side:'BUY',positionEffect:'OPEN',quantity:'1000000',executionPrice:'2',tradeDatetime:'2026-10-01T10:00:00Z',settlementDate:'',tradePurpose:'INVESTMENT',properties:{},tagIds:[],externalReferences:[],counterpartyOrganisationId:'bank'};
const context={tenantId:'tenant',bookedByUserAccountId:'actor',properties:[],tags:[]} as TradeBookingContext;
describe('swap ticket',()=>{
 it('shows full approved generic no-funding terms rather than legacy funding assumptions',()=>{
  const markup=renderToStaticMarkup(<ProductFacts terms={{...terms,swapDetails:{...terms.swapDetails!,genericTerms:generic,fundingReferenceId:null,fundingReferenceName:null,fundingSpread:null}}}/>);
  for(const value of ['Autocall swap','Contractual notional','1000000 GBP','2×','TOTAL','NONE','Confirmation reset schedule','Reinvest proceeds under section 6','Signed whole-swap confirmation','No separate funding leg','Leverage is not applied again'])expect(markup).toContain(value);
  expect(markup).not.toContain('Funding notional basis');expect(markup).not.toContain('Funding spread (decimal)');
 });
 it('shows approved excess-return funding acknowledgement and independent resets and payments',()=>{
  const markup=renderToStaticMarkup(<ProductFacts terms={{...terms,swapDetails:{...terms.swapDetails!,genericTerms:{...generic,returnBasis:'EXCESS',financingTreatment:'EMBEDDED_AND_SEPARATE',fundingReferenceId:'rate',fundingSpread:'-0.0015',fundingNotionalBasis:'LEVERAGED_NOMINAL',dayCountConventionId:'act365',interestCalculationMethod:'Compounded overnight',fundingObservationDescription:'Five day lag',fundingResetFrequency:'MONTHLY',fundingPaymentFrequency:'QUARTERLY',additionalFundingAcknowledged:true,additionalFundingEvidence:'Explicit extra funding charge'}}}}/>);
  for(const value of ['SONIA','EXCESS','EMBEDDED_AND_SEPARATE','LEVERAGED_NOMINAL','-0.0015','Compounded overnight','Five day lag','MONTHLY / QUARTERLY','Explicit extra funding charge'])expect(markup).toContain(value);
 });
 it.each([['BUY','2','8000'],['SELL','2','-8000'],['BUY','0','0'],['SELL','0','0'],['BUY','-2','-8000'],['SELL','-2','8000']])('reviews 2x whole-swap quote %s / %s once', (side,executionPrice,amount)=>{
  const markup=renderToStaticMarkup(<ProductReview terms={{...terms,swapDetails:{...terms.swapDetails!,genericTerms:generic}}} draft={{...draft,quantity:'400000',side:side as 'BUY'|'SELL',executionPrice}} context={context} strategies={[]}/>);
  expect(markup).toContain(`<dd>${amount} GBP</dd>`);expect(markup).toContain('Booked nominal');expect(markup).toContain('Contractual notional');
 });
 it('submits partial nominal and custom source fields without mutating the draft or generic terms',()=>{
  const approved={...terms,swapDetails:{...terms.swapDetails!,genericTerms:generic}};
  const edited={...draft,quantity:'400000',side:'SELL' as const,properties:{zero:'0',flag:false},tagIds:['tag'],comment:' source note ',externalReferences:[{referenceType:'SOURCE_TRADE_ID' as const,referenceValue:' source-1 ',sourceSystemId:' feed '}]};
  const before=structuredClone({approved,edited});const payload=buildProductPayload(approved,edited);
  expect(payload).toMatchObject({quantity:'400000',side:'SELL',expectedTermsFingerprint:'a'.repeat(64),properties:[{definitionId:'zero',value:'0'},{definitionId:'flag',value:false}],tagIds:['tag'],comment:'source note',externalReferences:[{referenceType:'SOURCE_TRADE_ID',referenceValue:'source-1',sourceSystemId:'feed'}]});
  expect({approved,edited}).toEqual(before);
 });
 it.each(['0','2','-1.5'])('allows exact signed quote %s without settlement',executionPrice=>{
  expect(validateProductDraft(terms,{...draft,executionPrice},context)).toEqual([]);
  const payload=buildProductPayload(terms,{...draft,executionPrice});expect(payload.executionPrice).toBe(executionPrice);expect(payload.settlementDate).toBeNull();
 });
 it('requires an explicit quote and counterparty',()=>{
  expect(validateProductDraft(terms,{...draft,executionPrice:''},context).some(e=>e.field==='executionPrice')).toBe(true);
  expect(validateProductDraft(terms,{...draft,counterpartyOrganisationId:''},context).some(e=>e.field==='counterpartyOrganisationId')).toBe(true);
 });
 it('uses quote divisor once',()=>{
  expect(productAmount(terms,'1000000','2')).toBe('20000');
  expect(productAmount({...terms,convention:{...terms.convention!,quoteFactor:'1'}},'1000000','.02')).toBe('20000');
 });
 it('reviews SELL as signed value rather than a RECEIVE cash amount',()=>{
  const markup=renderToStaticMarkup(<ProductReview terms={terms} draft={{...draft,side:'SELL'}} context={context} strategies={[]}/>);
  expect(markup).toContain('-20000 GBP');expect(markup).toContain('Entry reference value');expect(markup).not.toContain('RECEIVE 20000');expect(markup).not.toContain('Security settlement date');
 });
 it('shows inherited funding and no funded-note assumptions',()=>{
  const markup=renderToStaticMarkup(<ProductFacts terms={terms}/>);expect(markup).toContain('SONIA');expect(markup).toContain('Autocall reference');expect(markup).toContain('Funding spread');
 });
 it('offers a swap ticket without a listed route selector',()=>{
  const markup=renderToStaticMarkup(<ProductTicket kind="SWAP" strategies={[]} context={context}/>);
  expect(markup).toContain('Book swap');expect(markup).not.toContain('Listed execution');
 });
 it('configures a swap divisor rather than a funded security',()=>{
  const markup=renderToStaticMarkup(<ProductConventionForm kind="SWAP" currencies={[]} tenantId="tenant" instrumentId="swap" current={terms.convention}/>);
  expect(markup).toContain('Swap value per notional');expect(markup).toContain('Quote divisor');expect(markup).not.toContain('Fully funded note/certificate');
 });
});
