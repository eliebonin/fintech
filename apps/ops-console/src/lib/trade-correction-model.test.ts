import {expect,it} from 'vitest';
import {bookingCancellationEligibility,bookingCorrectionEligibility,bookingCorrectionLinks,withBookingCorrection} from './trade-correction-model';
import type {TradeDetailPayload} from './trades';
const id='00000000-0000-7000-8000-000000000001',next='00000000-0000-7000-8000-000000000002';
const detail={trade:{tradeId:id,lifecycleStatus:'BOOKED',tradeType:'INVESTMENT',strategyId:'strategy'},lifecycleEvents:[{sequenceNo:1,eventType:'BOOKED',eventPayload:JSON.stringify({schemaVersion:1,kind:'CASH_BOOKING'})}]} as TradeDetailPayload['data'];
it('legacy cancellation rejects malformed evidence, missing history and new metadata',()=>{
 const legacy={...detail,lifecycleEvents:[{...detail.lifecycleEvents[0],eventPayload:'{}'}]};
 expect(bookingCancellationEligibility(legacy).eligible).toBe(true);
 for(const raw of ['{broken','null','[]','{"kind":"UNKNOWN"}'])expect(bookingCancellationEligibility({...legacy,lifecycleEvents:[{...legacy.lifecycleEvents[0],eventPayload:raw}]}).eligible).toBe(false);
 expect(bookingCancellationEligibility({...legacy,lifecycleEvents:[]}).eligible).toBe(false);
 expect(bookingCancellationEligibility({...legacy,trade:{...legacy.trade,valuationDateBasis:'UTC_TRADE_DATE',valuationEffectiveDate:'2026-10-01'}}).eligible).toBe(false);
});
it('keeps ordinary payload unchanged and attaches correction only explicitly',()=>{
 const payload={strategyId:'strategy',quantity:'10'};expect(withBookingCorrection(payload)).toBe(payload);
 const correction={tradeId:id,expectedSequenceNo:1,reason:'Wrong quantity'};
 expect(withBookingCorrection(payload,correction)).toEqual({...payload,correction});expect(payload).not.toHaveProperty('correction');
});
it('allows supported active snapshot chains and refuses unknown lifecycle or absent history',()=>{
 expect(bookingCorrectionEligibility(detail)).toEqual({eligible:true,sequenceNo:1,product:'CASH'});
 expect(bookingCorrectionEligibility({...detail,lifecycleEvents:[]} ).eligible).toBe(false);
 expect(bookingCorrectionEligibility({...detail,trade:{...detail.trade,lifecycleStatus:'CANCELLED'}}).eligible).toBe(false);
 expect(bookingCorrectionEligibility({...detail,lifecycleEvents:[...detail.lifecycleEvents,{sequenceNo:2,eventType:'NOVATED'} as any]}).eligible).toBe(false);
});
it('returns only validated lineage and human reason from correction evidence',()=>{
 const corrected={...detail,lifecycleEvents:[...detail.lifecycleEvents,{sequenceNo:2,eventType:'CORRECTED',eventPayload:JSON.stringify({schemaVersion:1,kind:'BOOKING_CORRECTION',action:'REPLACES_BOOKING',originalTradeId:next,replacementTradeId:id,reason:'Wrong price'})} as any]};
 expect(bookingCorrectionEligibility(corrected).eligible).toBe(true);
 expect(bookingCorrectionLinks(corrected.lifecycleEvents[1])).toEqual({originalTradeId:next,replacementTradeId:id,reason:'Wrong price'});
 expect(bookingCorrectionLinks({eventPayload:'{bad'} as any)).toBeNull();
 expect(bookingCorrectionLinks({eventPayload:JSON.stringify({schemaVersion:1,kind:'BOOKING_CORRECTION',originalTradeId:'https://evil',reason:'bad'})} as any)).toBeNull();
 for(const invalid of [{originalTradeId:next,replacementTradeId:next,reason:'Wrong ID'},{originalTradeId:id,replacementTradeId:id,reason:'Self link'},{originalTradeId:next,replacementTradeId:id,reason:'   '}]){
   const event={...corrected.lifecycleEvents[1],eventPayload:JSON.stringify({schemaVersion:1,kind:'BOOKING_CORRECTION',action:'REPLACES_BOOKING',...invalid})};
   expect(bookingCorrectionEligibility({...detail,lifecycleEvents:[...detail.lifecycleEvents,event]}).eligible).toBe(false);
 }
});
