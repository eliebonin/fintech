import {browserFetch} from '@/lib/browser-fetch';
import type {components} from 'api-contracts';
export type WorklistResult=components['schemas']['WorklistView'];
export type WorklistEvent=components['schemas']['WorklistEvent'];
export type CouponView=components['schemas']['CouponInspection'];
export type FutureView=components['schemas']['FutureInspection'];
export type OptionView=components['schemas']['OptionInspection'];
export type StructuredView=components['schemas']['StructuredInspection'];
export const milestoneLabels:Record<string,string>={LAST_TRADE:'Last trading cutoff',EXPIRY:'Contract expiry',FINAL_SETTLEMENT:'Final settlement',DELIVERY_START:'Delivery window opens',DELIVERY_END:'Delivery window ends',SOURCE_REVIEW:'Contract source review',COUPON_OBSERVATION:'Coupon observation',AUTOCALL_OBSERVATION:'Potential autocall observation',OBSERVATION:'Scheduled observation',FINAL_VALUATION:'Final valuation',MATURITY:'Contractual maturity',SOURCE_UNAVAILABLE:'Schedule information unavailable'};
export type StrategyOptions=components['schemas']['WorklistOptions'];
export const eventLabels={ALL:'All events',BOND_MATURITY:'Bond maturity',FX_FORWARD_MATURITY:'FX-forward maturity',BOND_COUPON:'Bond coupon',FUTURE_EXPIRY:'Futures milestones',OPTION_EXPIRY:'Option expiry',STRUCTURED_OBSERVATION:'Structured product schedules'} as const;
export type Filters={eventType?:keyof typeof eventLabels;fromDate:string;toDate:string;strategyId:string;strategyLabel:string;instrumentQuery?:string;attention:string;status:string;includeEarlierOverdue:boolean;offset:number;limit:25|50|100};
export const statusLabels:Record<string,string>={UPCOMING:'Upcoming',DUE:'Due today',OVERDUE:'Overdue',PREPARED:'Prepared',BOOKED:'Booked · exposure closed',REASSESSMENT:'Reassessment needed',BLOCKED:'Blocked · review needed',REVIEW_DUE:'Review due · receipt not assessed',CONFIRMATION_RECORDED:'Confirmation recorded',SCHEDULED_TODAY:'Scheduled today · outcome not assessed',DATE_PASSED:'Date passed · outcome not assessed',SOURCE_UNAVAILABLE:'Information unavailable'};
export function queryFor(filters:Filters){const q=new URLSearchParams({fromDate:filters.fromDate,toDate:filters.toDate,eventType:filters.eventType??'ALL',attention:filters.attention,status:filters.status,includeEarlierOverdue:String(filters.includeEarlierOverdue),offset:String(filters.offset),limit:String(filters.limit)});if(filters.strategyId)q.set('strategyId',filters.strategyId);if(filters.instrumentQuery?.trim())q.set('q',filters.instrumentQuery.trim());return q;}
export async function worklistRead<T>(tenantId:string,path:string,signal?:AbortSignal):Promise<T>{
 // Do not start requests for effects discarded before the next microtask
 // (including development StrictMode cleanup). No cache or shared identity.
 await Promise.resolve();signal?.throwIfAborted();
 const response=await browserFetch(`/api/lifecycle/${path}`,{cache:'no-store',headers:{'X-Expected-Tenant-Id':tenantId},signal:signal?AbortSignal.any([signal,AbortSignal.timeout(45000)]):AbortSignal.timeout(45000)});
 const body=await response.json();if(!response.ok)throw new Error(body.error?.message??body.detail??'The lifecycle worklist could not be loaded.');return body as T;
}
