import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {InstrumentDetail} from './instrument-detail';
import {getInstrument} from '@/lib/instrument-data';
import type {components} from 'api-contracts';
const terms:components['schemas']['GenericSwapTerms-Output']={schemaVersion:1,tenantIdentifier:'SW-1',performanceReferenceId:'reference',contractualNotional:'1000000.123456789012',notionalCurrencyId:'gbp',effectiveDate:'2026-10-03',maturityDate:'2027-10-03',performanceDirection:'RECEIVE',returnBasis:'TOTAL',returnProfileId:'total',leverage:'2',quoteCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Signed confirmation',financingTreatment:'SEPARATE',fundingReferenceId:'sonia',fundingSpread:'-0.0015',fundingNotionalBasis:'BOOKED_NOMINAL',dayCountConventionId:'act365',interestCalculationMethod:'Compounded overnight',fundingResetFrequency:'MONTHLY',fundingPaymentFrequency:'QUARTERLY',additionalFundingAcknowledged:false,performanceResetFrequency:'CUSTOM',performanceScheduleDescription:'Confirmation reset dates',redemptionRule:'CONTINUE',continuationDescription:'Sourced replacement rule'};
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
