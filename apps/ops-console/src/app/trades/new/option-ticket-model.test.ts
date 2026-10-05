import { describe,it,expect } from 'vitest';
import { previewOptionPremium,validateOptionTicketDraft,buildOptionTicketPayload,type OptionTicketDraft } from './option-ticket-model';
import type { OptionBookingListingView,TradeBookingContext } from '@/lib/browser-api-client';
const terms={listingId:'listing',instrumentId:'instrument',name:'Call',listingName:'Call listing',optionType:'CALL',premiumMultiplier:'100',quoteFactor:'1',premiumCurrency:'GBP',lastTradingAtUtc:'2027-09-17T16:30:00Z',bookingEligible:true,termsFingerprint:'a'.repeat(64)} as OptionBookingListingView;
const context={properties:[],tags:[]} as unknown as TradeBookingContext;
const draft:OptionTicketDraft={strategyId:'strategy',side:'BUY',positionEffect:'OPEN',quantity:'10',executionPrice:'2.5',tradeDatetime:'2026-10-01T10:00:00Z',settlementDate:'2026-10-05',tradePurpose:'INVESTMENT',properties:{},tagIds:[],externalReferences:[]};
describe('option ticket economics',()=>{
  it('accepts scientific API multipliers and divisors without changing quoted premium',()=>{
    expect(previewOptionPremium({...terms,premiumMultiplier:'1E+2',quoteFactor:'1E+2'},'10','250')).toBe('2500');
  });
  it('converts major and minor quoted premiums exactly',()=>{expect(previewOptionPremium(terms,'10','2.5')).toBe('2500');expect(previewOptionPremium({...terms,quoteFactor:'100'},'10','250')).toBe('2500');});
  it('accepts zero premium and rejects unrepresentable previews',()=>{expect(previewOptionPremium(terms,'10','0')).toBe('0');expect(previewOptionPremium({...terms,quoteFactor:'3'},'1','1')).toBe('—');expect(previewOptionPremium(terms,'','2')).toBe('—');});
  it('requires integer contracts and explicit premium date',()=>{expect(validateOptionTicketDraft(terms,draft,context)).toEqual([]);expect(validateOptionTicketDraft(terms,{...draft,quantity:'1.5',settlementDate:''},context).map(e=>e.field)).toEqual(expect.arrayContaining(['quantity','settlementDate']));});
  it('rejects execution past cutoff but accepts exact cutoff',()=>{expect(validateOptionTicketDraft(terms,{...draft,tradeDatetime:'2027-09-17T16:30:00Z',settlementDate:'2027-09-20'},context)).toEqual([]);expect(validateOptionTicketDraft(terms,{...draft,tradeDatetime:'2027-09-17T16:30:01Z'},context).map(e=>e.field)).toContain('tradeDatetime');});
  it('preserves governed fields, zero and false annotations',()=>{const payload=buildOptionTicketPayload(terms,{...draft,side:'SELL',positionEffect:'CLOSE',properties:{zero:'0',flag:false,empty:''}});expect(payload.positionEffect).toBe('CLOSE');expect(payload.properties).toEqual([{definitionId:'zero',value:'0'},{definitionId:'flag',value:false}]);expect(payload).not.toHaveProperty('premiumMultiplier');});
});
