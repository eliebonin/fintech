import type {TradeDetailPayload,TradeLifecycleEvent} from './trades';
export type BookingCorrection={tradeId:string;expectedSequenceNo:number;reason:string};
export type BookingProduct='CASH'|'FX_FORWARD'|'OPTION'|'STRUCTURED_PRODUCT'|'FUTURE'|'BOND'|'SWAP';
const products:BookingProduct[]=['CASH','FX_FORWARD','OPTION','STRUCTURED_PRODUCT','FUTURE','BOND','SWAP'];
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function payload(event:TradeLifecycleEvent):Record<string,any>|null {
 try{const value=JSON.parse(event.eventPayload??'null');return value&&typeof value==='object'&&!Array.isArray(value)?value:null;}catch{return null;}
}
export function withBookingCorrection<T extends object>(value:T,correction?:BookingCorrection):T&{correction?:BookingCorrection} {
 return correction?{...value,correction}:value;
}
export function bookingCorrectionLinks(event:TradeLifecycleEvent) {
 const value=payload(event);
 if(value?.schemaVersion!==1||value.kind!=='BOOKING_CORRECTION'||!uuid.test(value.originalTradeId??'')||typeof value.reason!=='string')return null;
 if(value.replacementTradeId!==undefined&&!uuid.test(value.replacementTradeId))return null;
 return {originalTradeId:value.originalTradeId as string,replacementTradeId:value.replacementTradeId as string|undefined,reason:value.reason as string};
}
export function bookingCorrectionEligibility(detail:TradeDetailPayload['data']):{eligible:boolean;sequenceNo:number;product?:BookingProduct} {
 const events=detail.lifecycleEvents;
 const no={eligible:false,sequenceNo:events.at(-1)?.sequenceNo??0};
 if(detail.trade.lifecycleStatus!=='BOOKED'||detail.trade.tradeType!=='INVESTMENT'||!events.length||events.length>2||events.some((event,index)=>event.sequenceNo!==index+1)||events[0].eventType!=='BOOKED')return no;
 const first=payload(events[0]);
 if(first?.schemaVersion!==1)return no;
 const kind=first.kind==='PRODUCT_BOOKING'?first.economics?.terms?.kind:({CASH_BOOKING:'CASH',FX_FORWARD_BOOKING:'FX_FORWARD',OPTION_BOOKING:'OPTION'} as Record<string,string>)[first.kind];
 if(!products.includes(kind))return no;
 if(events.length===2){const links=bookingCorrectionLinks(events[1]);if(events[1].eventType!=='CORRECTED'||payload(events[1])?.action!=='REPLACES_BOOKING'||!links||links.replacementTradeId!==detail.trade.tradeId||links.originalTradeId===detail.trade.tradeId||!links.reason.trim())return no;}
 return {eligible:true,sequenceNo:events.at(-1)!.sequenceNo,product:kind};
}

export function bookingCancellationEligibility(detail:TradeDetailPayload['data']):{eligible:boolean;sequenceNo:number;legacy:boolean} {
 const regular=bookingCorrectionEligibility(detail);
 if(regular.eligible)return {...regular,legacy:false};
 const events=detail.lifecycleEvents,first=events[0],value=first&&payload(first);
 const empty=first&&(first.eventPayload==null||first.eventPayload===''||(value&&Object.keys(value).length===0));
 const trade=detail.trade;
 const validTime=!first?.eventDatetimeUtc||Date.parse(first.eventDatetimeUtc)===Date.parse(trade.tradeDatetimeUtc);
 const legacyRecognition=trade.valuationDateBasis==='LEGACY_UTC_TRADE_DATE'||(!trade.valuationEffectiveDate&&!trade.valuationDateBasis);
 const eligible=trade.lifecycleStatus==='BOOKED'&&trade.tradeType==='INVESTMENT'&&events.length===1&&first.sequenceNo===1&&first.eventType==='BOOKED'&&!!empty&&validTime&&
  legacyRecognition&&!trade.valuationOverrideReason;
 return {eligible,sequenceNo:events.at(-1)?.sequenceNo??0,legacy:eligible};
}
