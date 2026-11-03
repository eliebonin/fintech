import {expect,it} from 'vitest';
import {buildFutureConvention} from './future-form-model';
import type {components} from 'api-contracts';
type Convention=Extract<NonNullable<components['schemas']['ProductBookingContextView']['convention']>,{kind:'FUTURE'}>;
const current:Convention={kind:'FUTURE',quantityUnit:'CONTRACTS',effectiveFrom:'2026-09-01',priceCurrencyId:'usd',sourceReference:'Synthetic source',
 priceBasis:'UNDERLYING_UNIT',settlementMethod:'PHYSICAL',contractSize:'5',contractSizeCurrencyId:'btc',monetaryMultiplier:'5',quoteFactor:'1',tickSize:'5',allowNegativePrice:false,
 lastTradingAtUtc:'2027-03-17T16:00:00Z',finalSettlementDate:'2027-03-19',deliveryStartDate:'2027-03-19',deliveryEndDate:'2027-03-19'};
const fields={effectiveFrom:'2026-10-01',priceCurrencyId:'changed',sourceReference:'Reviewed source',quoteFactor:'100',monetaryMultiplier:'99',tickSize:'1',
 lastTradingAtUtc:'2027-04-01T16:00:00Z',finalSettlementDate:'2027-04-02',deliveryStartDate:'2027-04-02',deliveryEndDate:'2027-04-02'};
it('preserves actual crypto quotation, currency, size and delivery dates on convention amendment',()=>{
 const next=buildFutureConvention(fields,true,current);
 expect(next).toEqual({...current,effectiveFrom:fields.effectiveFrom,sourceReference:'Reviewed source'});
});
it('inherits new physical contract economics from its approved family without copying unrelated family fields',()=>{
 const spec={underlyingKind:'CRYPTOASSET' as const,symbolRoot:'BTC',yearDigits:2 as const,deliveryMonths:[3,6,9,12],
  priceBasis:'UNDERLYING_UNIT' as const,settlementMethod:'PHYSICAL' as const,contractSize:'5',contractSizeCurrencyId:'btc',monetaryMultiplier:'5',quoteFactor:'1',tickSize:'5',allowNegativePrice:false};
 const result=buildFutureConvention({...fields,priceCurrencyId:'usd'},true,spec);
 expect(result.priceBasis).toBe('UNDERLYING_UNIT');expect(result.contractSize).toBe('5');expect(result.deliveryStartDate).toBe(fields.deliveryStartDate);
 expect(result).not.toHaveProperty('deliveryMonths');expect(result).not.toHaveProperty('underlyingKind');
});
it('retains the existing legacy index creation defaults',()=>{
 const result=buildFutureConvention({...fields,priceCurrencyId:'usd'},false);
 expect(result.priceBasis).toBe('INDEX_POINTS');expect(result.settlementMethod).toBe('CASH');expect(result.deliveryStartDate).toBeNull();
});
