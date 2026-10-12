import {describe,it,expect} from 'vitest';
import {productAmount,buildProductPayload,type ProductTerms,type ProductDraft} from './product-ticket-model';
const common={effectiveFrom:'2026-09-01',priceCurrencyId:'currency',quoteFactor:'100',sourceReference:'Terms'};
const note:ProductTerms={instrumentId:'note',name:'Note',kind:'STRUCTURED_PRODUCT',executionRoute:'OTC',bookingEligible:true,convention:{...common,kind:'STRUCTURED_PRODUCT',funding:'FULLY_FUNDED',quantityUnit:'NOMINAL',priceBasis:'PCT_OF_PAR',quantityMinimum:'1000',quantityIncrement:'1000',accrual:'NONE',otcAllowed:true}};
const future:ProductTerms={instrumentId:'future',name:'Future',kind:'FUTURE',executionRoute:'LISTED',listingId:'listing',bookingEligible:true,convention:{...common,kind:'FUTURE',quoteFactor:'1',quantityUnit:'CONTRACTS',priceBasis:'INDEX_POINTS',settlementMethod:'CASH',monetaryMultiplier:'5',tickSize:'.25',allowNegativePrice:true,lastTradingAtUtc:'2027-03-19T13:30:00Z',finalSettlementDate:'2027-03-19'}};
describe('exact product preview',()=>{
  it('sends platform recognition independently of product terms and custom properties',()=>{
    const draft={strategyId:'s',side:'BUY',quantity:'2',executionPrice:'6000',tradeDatetime:'2026-10-01T10:00:00Z',settlementDate:'',positionEffect:'OPEN',tradePurpose:'INVESTMENT',properties:{},tagIds:[],externalReferences:[],valuationEffectiveDate:'2026-10-02',valuationOverrideReason:'Deferred'} as ProductDraft;
    for(const terms of [note,future]){
      const payload=buildProductPayload(terms,draft);expect(payload.valuationEffectiveDate).toBe('2026-10-02');expect(payload.valuationOverrideReason).toBe('Deferred');
    }
  });
  it('uses exponent-serialized convention decimals without rounding',()=>{
    const wireFuture={...future,convention:{...future.convention!,quoteFactor:'1E+0',monetaryMultiplier:'5E+0'}} as ProductTerms;
    expect(productAmount(wireFuture,'2','-1.25E+0')).toBe('-12.5');
  });
  it('normalizes only exact supported scientific values',()=>{
    expect(productAmount(note,'100000','1000E-3')).toBe('1000');
    expect(productAmount(note,'100000','100E-14')).toBe('0.000000001');
    for(const price of ['1E-13','1E18','1E-1000000','1.23E','Infinity'])expect(productAmount(note,'1',price)).toBe('—');
  });
  it('uses nominal percentage economics',()=>expect(productAmount(note,'100000','98.5')).toBe('98500'));
  it('uses denomination once for unit percentage economics',()=>expect(productAmount({...note,convention:{...note.convention!,kind:'STRUCTURED_PRODUCT',funding:'FULLY_FUNDED',quantityUnit:'UNITS',priceBasis:'PCT_OF_PAR',denomination:'1000',quantityMinimum:'1',quantityIncrement:'1',accrual:'NONE',otcAllowed:true}},'100','98.5')).toBe('98500'));
  it('uses signed futures quote and multiplier',()=>{expect(productAmount(future,'2','6000')).toBe('60000');expect(productAmount(future,'2','-1.25')).toBe('-12.5');expect(productAmount(future,'2','0')).toBe('0');});
  it('rejects silent precision loss',()=>expect(productAmount({...future,convention:{...future.convention!,kind:'FUTURE',quantityUnit:'CONTRACTS',priceBasis:'INDEX_POINTS',settlementMethod:'CASH',monetaryMultiplier:'5',tickSize:'.25',allowNegativePrice:true,lastTradingAtUtc:'2027-03-19T13:30:00Z',finalSettlementDate:'2027-03-19',quoteFactor:'3'}},'1','1')).toBe('—'));
  it('does not send a cash settlement date for futures and retains zero annotations',()=>{
    const draft={strategyId:'s',side:'BUY',quantity:'2',executionPrice:'6000',tradeDatetime:'2026-10-01T10:00:00Z',settlementDate:'2026-10-05',positionEffect:'OPEN',tradePurpose:'INVESTMENT',properties:{zero:'0',flag:false},tagIds:[],externalReferences:[]} as ProductDraft;
    const payload=buildProductPayload(future,draft);expect(payload.settlementDate).toBeNull();expect(payload.properties).toEqual([{definitionId:'zero',value:'0'},{definitionId:'flag',value:false}]);
  });
});
