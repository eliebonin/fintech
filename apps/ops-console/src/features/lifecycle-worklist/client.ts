import {browserFetch} from '@/lib/browser-fetch';
import type {components} from 'api-contracts';
export type WorklistResult=components['schemas']['WorklistView'];
export type WorklistEvent=components['schemas']['WorklistEvent'];
export type StrategyOptions=components['schemas']['WorklistOptions'];
export type Filters={fromDate:string;toDate:string;strategyId:string;strategyLabel:string;instrumentQuery?:string;attention:string;status:string;includeEarlierOverdue:boolean;offset:number;limit:25|50|100};
export const statusLabels:Record<string,string>={UPCOMING:'Upcoming',DUE:'Due today',OVERDUE:'Overdue',PREPARED:'Prepared',BOOKED:'Booked · exposure closed',REASSESSMENT:'Reassessment needed',BLOCKED:'Blocked · review needed'};
export function queryFor(filters:Filters){const q=new URLSearchParams({fromDate:filters.fromDate,toDate:filters.toDate,attention:filters.attention,status:filters.status,includeEarlierOverdue:String(filters.includeEarlierOverdue),offset:String(filters.offset),limit:String(filters.limit)});if(filters.strategyId)q.set('strategyId',filters.strategyId);if(filters.instrumentQuery?.trim())q.set('q',filters.instrumentQuery.trim());return q;}
export async function worklistRead<T>(tenantId:string,path:string,signal?:AbortSignal):Promise<T>{
 // Do not start requests for effects discarded before the next microtask
 // (including development StrictMode cleanup). No cache or shared identity.
 await Promise.resolve();signal?.throwIfAborted();
 const response=await browserFetch(`/api/lifecycle/${path}`,{cache:'no-store',headers:{'X-Expected-Tenant-Id':tenantId},signal:signal?AbortSignal.any([signal,AbortSignal.timeout(45000)]):AbortSignal.timeout(45000)});
 const body=await response.json();if(!response.ok)throw new Error(body.error?.message??body.detail??'The lifecycle worklist could not be loaded.');return body as T;
}
