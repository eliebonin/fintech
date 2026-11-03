import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {InstrumentDetail} from './instrument-detail';
import {getInstrument} from '@/lib/instrument-data';
import type {components} from 'api-contracts';
import {SwapTermsFacts} from './swap-terms-facts';
import {swapContextLabels} from '@/lib/trade-history';
it('shows each floating leg and its own currency without a performance-return label',()=>{
  const leg={contractualNotional:'34700000',direction:'PAY' as const,rateReferenceId:'sofr',currencyId:'usd',spread:'0',dayCountConventionId:'act360',interestCalculationMethod:'Compounded overnight',observationDescription:'Confirmation section 4',resetFrequency:'QUARTERLY' as const,paymentFrequency:'QUARTERLY' as const};
  const rate:components['schemas']['RateSwapTerms-Output']={schemaVersion:1,swapKind:'RATE_EXCHANGE',quantityUnit:'NOMINAL',contractualNotional:'26000000',notionalCurrencyId:'gbp',quoteCurrencyId:'gbp',quoteFactor:'1',effectiveDate:'2026-10-01',maturityDate:'2027-10-01',sourceReference:'Two-leg confirmation',principalExchange:'UNSPECIFIED',principalExchangeDescription:'Not assessed from source',legs:[leg,{...leg,direction:'RECEIVE',currencyId:'gbp',rateReferenceId:'sonia',contractualNotional:'26000000',spread:'0.00135'}]};
  const html=renderToStaticMarkup(<SwapTermsFacts terms={rate} labels={{gbp:'GBP',usd:'USD',sofr:'SOFR',sonia:'SONIA',act360:'Actual / 360'}}/>);
  for(const text of ['Rate-exchange swap terms','SOFR','SONIA','34,700,000','26,000,000','13.5 bps','Not assessed from source'])expect(html).toContain(text);
  expect(html).not.toContain('Performance swap terms');expect(html).not.toContain('Return basis / governed profile');
  const context:components['schemas']['ProductBookingContextView']={instrumentId:'swap',name:'Rate exchange',kind:'SWAP',executionRoute:'OTC',bookingEligible:true,swapDetails:{effectiveDate:rate.effectiveDate,genericTerms:rate,sourceFacts:{rateReferences:[{reference_node_id:'sofr',canonical_name:'Frozen SOFR name'}],currencies:[{currency_id:'usd',currency_code:'USD'}],dayCountConventions:[{day_count_convention_id:'act360',display_name:'Actual / 360'}]}}};
  expect(swapContextLabels(context)).toEqual({sofr:'Frozen SOFR name',usd:'USD',act360:'Actual / 360'});
});
const terms:components['schemas']['GenericSwapTerms-Output']={schemaVersion:1,quantityUnit:'NOMINAL',tenantIdentifier:'SW-1',performanceReferenceId:'reference',contractualNotional:'1000000.123456789012',notionalCurrencyId:'gbp',effectiveDate:'2026-10-03',maturityDate:'2027-10-03',performanceDirection:'RECEIVE',returnBasis:'TOTAL',returnProfileId:'total',leverage:'2',quoteCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Signed confirmation',financingTreatment:'SEPARATE',fundingReferenceId:'sonia',fundingSpread:'-0.0015',fundingNotionalBasis:'BOOKED_NOMINAL',dayCountConventionId:'act365',interestCalculationMethod:'Compounded overnight',fundingResetFrequency:'MONTHLY',fundingPaymentFrequency:'QUARTERLY',additionalFundingAcknowledged:false,performanceResetFrequency:'CUSTOM',performanceScheduleDescription:'Confirmation reset dates',redemptionRule:'CONTINUE',continuationDescription:'Sourced replacement rule'};
it('renders approved swap terms and governed reference links through the existing detail renderer',()=>{
  const instrument={...getInstrument('0198f4de-2fb5-7b8b-8c0d-000000000101')!,instrumentType:'SWAP',genericTerms:terms};
  const html=renderToStaticMarkup(<InstrumentDetail instrument={instrument} swapLabels={{reference:'Approved equity',sonia:'SONIA',gbp:'GBP',total:'Governed total return',act365:'Actual / 365'}}/>);
  expect(html).toContain('Performance swap terms');expect(html).toContain('1000000.123456789012');expect(html).toContain('SW-1');expect(html).toContain('-0.0015');expect(html).toContain('Sourced replacement rule');expect(html).toContain('q=reference');expect(html).toContain('q=sonia');expect(html).toContain('RATE_INDEX');expect(html).toContain('signed booked nominal');
  expect(html).toContain('Approved equity');expect(html).toContain('SONIA');expect(html).toContain('GBP');expect(html).toContain('Actual / 365');
});
it('preserves legacy swap detail when typed generic terms are absent',()=>{
  const instrument={...getInstrument('0198f4de-2fb5-7b8b-8c0d-000000000101')!,instrumentType:'SWAP'};
  const html=renderToStaticMarkup(<InstrumentDetail instrument={instrument}/>);
  expect(html).toContain('Booking conventions');expect(html).not.toContain('Performance swap terms');
});
