import {browserFetch} from '@/lib/browser-fetch';
export type Page<T>={items:T[];total:number;offset:number;limit:number};
export type Source={sourceKey:string;kind:'CUSTOM'|'CANONICAL';code:string;label:string;status:string;description?:string|null;catalogueId?:string;activeEntryCount:number;fieldCount:number};
export type Entry={recordVersionId:string;recordId:string;code:string;label:string;description:string|null;versionNo:number;status:string};
export type Usage={kind?:'FIELD'|'PROFILE'|'STRATEGY';identity?:string;definitionId:string;code:string;label:string;versionNo:number;status:string};
export type History={eventId:string;action:string;subjectId:string|null;reason:string;recordedAtUtc:string};
export async function referenceRequest<T>(tenantId:string,path:string):Promise<T>{
 const response=await browserFetch(`/api/tenant-reference/${path}`,{cache:'no-store',headers:{'X-Expected-Tenant-Id':tenantId},signal:AbortSignal.timeout(35000)});
 const result=await response.json();if(!response.ok)throw new Error(result.error?.message??result.detail??'Reference data could not be loaded.');return result as T;
}
