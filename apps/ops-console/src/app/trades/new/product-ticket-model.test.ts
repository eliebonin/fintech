import {describe,it,expect} from 'vitest';
import {productAmount,buildProductPayload,type ProductTerms,type ProductDraft} from './product-ticket-model';
const common={effectiveFrom:'2026-09-01',priceCurrencyId:'currency',quoteFactor:'100',sourceReference:'Terms'};
const note:ProductTerms={instrumentId:'note',name:'Note',kind:'STRUCTURED_PRODUCT',executionRoute:'OTC',bookingEligible:true,convention:{...common,kind:'STRUCTURED_PRODUCT',funding:'FULLY_FUNDED',quantityUnit:'NOMINAL',priceBasis:'PCT_OF_PAR',quantityMinimum:'1000',quantityIncrement:'1000',accrual:'NONE',otcAllowed:true}};
const future:ProductTerms={instrumentId:'future',name:'Future',kind:'FUTURE',executionRoute:'LISTED',listingId:'listing',bookingEligible:true,convention:{...common,kind:'FUTURE',quoteFactor:'1',quantityUnit:'CONTRACTS',priceBasis:'INDEX_POINTS',settlementMethod:'CASH',monetaryMultiplier:'5',tickSize:'.25',allowNegativePrice:true,lastTradingAtUtc:'2027-03-19T13:30:00Z',finalSettlementDate:'2027-03-19'}};
describe('exact product preview',()=>{
  it('uses nominal percentage economics',()=>expect(productAmount(note,'100000','98.5')).toBe('98500'));
  it('uses denomination once for unit percentage economics',()=>expect(productAmount({...note,convention:{...note.convention!,kind:'STRUCTURED_PRODUCT',funding:'FULLY_FUNDED',quantityUnit:'UNITS',priceBasis:'PCT_OF_PAR',denomination:'1000',quantityMinimum:'1',quantityIncrement:'1',accrual:'NONE',otcAllowed:true}},'100','98.5')).toBe('98500'));
  it('uses signed futures quote and multiplier',()=>{expect(productAmount(future,'2','6000')).toBe('60000');expect(productAmount(future,'2','-1.25')).toBe('-12.5');expect(productAmount(future,'2','0')).toBe('0');});
  it('rejects silent precision loss',()=>expect(productAmount({...future,convention:{...future.convention!,kind:'FUTURE',quantityUnit:'CONTRACTS',priceBasis:'INDEX_POINTS',settlementMethod:'CASH',monetaryMultiplier:'5',tickSize:'.25',allowNegativePrice:true,lastTradingAtUtc:'2027-03-19T13:30:00Z',finalSettlementDate:'2027-03-19',quoteFactor:'3'}},'1','1')).toBe('—'));
  it('does not send a cash settlement date for futures and retains zero annotations',()=>{
    const draft={strategyId:'s',side:'BUY',quantity:'2',executionPrice:'6000',tradeDatetime:'2026-10-01T10:00:00Z',settlementDate:'2026-10-05',positionEffect:'OPEN',tradePurpose:'INVESTMENT',properties:{zero:'0',flag:false},tagIds:[],externalReferences:[]} as ProductDraft;
    const payload=buildProductPayload(future,draft);expect(payload.settlementDate).toBeNull();expect(payload.properties).toEqual([{definitionId:'zero',value:'0'},{definitionId:'flag',value:false}]);
  });
});
