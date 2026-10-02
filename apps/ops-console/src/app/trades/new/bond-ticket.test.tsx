import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {bondAmounts,buildProductPayload,type ProductTerms,type ProductDraft} from './product-ticket-model';
import {ProductFacts,ProductReview} from './product-ticket';
import type {TradeBookingContext} from '@/lib/browser-api-client';
const terms:ProductTerms={instrumentId:'bond',name:'Bond',kind:'BOND',executionRoute:'OTC',currency:'GBP',maturityDate:'2030-01-01',couponType:'FIXED',bookingEligible:true,termsFingerprint:'a'.repeat(64),
  convention:{kind:'BOND',effectiveFrom:'2026-09-01',priceCurrencyId:'gbp',quoteFactor:'100',sourceReference:'Sourced plain fixed bond',quantityUnit:'NOMINAL',priceBasis:'PCT_OF_PAR',principalBasis:'UNADJUSTED_NOMINAL',quantityMinimum:'1000',quantityIncrement:'1000',accrual:'MANUAL_CONFIRMATION',otcAllowed:true}};
const draft:ProductDraft={strategyId:'s',side:'BUY',positionEffect:'OPEN',quantity:'100000',executionPrice:'98.5',tradeDatetime:'2026-10-02T10:00:00Z',settlementDate:'2026-10-05',tradePurpose:'INVESTMENT',properties:{},tagIds:[],externalReferences:[],priceType:'CLEAN',accruedInterestAmount:'1250',settlementEvidence:'Confirmation verifying accrual and eligible settlement'};
describe('bond ticket economics',()=>{
  it.each([['CLEAN','98.5','1250','99750'],['DIRTY','99.75','1250','99750'],['CLEAN','98.5','-250','98250'],['DIRTY','98.25','-250','98250']])('does not double count %s', (priceType,executionPrice,accruedInterestAmount,dirty)=>{
    expect(bondAmounts(terms,{...draft,priceType:priceType as 'CLEAN'|'DIRTY',executionPrice,accruedInterestAmount})).toEqual({clean:'98500',dirty});
  });
  it('requires explicit accrued interest and price type',()=>{
    expect(bondAmounts(terms,{...draft,accruedInterestAmount:''})).toBeNull();
    expect(bondAmounts(terms,{...draft,priceType:''})).toBeNull();
    expect(bondAmounts(terms,{...draft,accruedInterestAmount:'0'})).toEqual({clean:'98500',dirty:'98500'});
  });
  it('retains evidence and does not send futures intent',()=>{const payload=buildProductPayload(terms,draft);expect(payload.positionEffect).toBeNull();expect(payload.accruedInterestAmount).toBe('1250');expect(payload.settlementEvidence).toBe(draft.settlementEvidence);});
  it('displays nominal scope and immutable review breakdown',()=>{
    const facts=renderToStaticMarkup(<ProductFacts terms={terms}/>);expect(facts).toContain('UNADJUSTED_NOMINAL');expect(facts).toContain('Maturity');
    const context={properties:[],tags:[],bookedByUserAccountId:'actor'} as unknown as TradeBookingContext;
    const review=renderToStaticMarkup(<ProductReview terms={terms} draft={draft} context={context} strategies={[]}/>);
    expect(review).toContain('PAY 99750 GBP');expect(review).toContain('98500 GBP');expect(review).toContain('Total signed accrued interest');expect(review).toContain(draft.settlementEvidence!);
  });
});
