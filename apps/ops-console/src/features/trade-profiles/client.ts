import {browserFetch} from '@/lib/browser-fetch';
import type {components} from 'api-contracts';
export type Page<T>={items:T[];total:number;offset:number;limit:number};
export type ProfileRow=components['schemas']['ProfileRow'];
export type ProfileVersion=components['schemas']['VersionView'];
export type ProfileContext=components['schemas']['ConfigurationView'];
export type Rule=components['schemas']['FieldRule'];
export type DefaultProfile=components['schemas']['DefaultView'];
export type FieldOption={definitionId:string;code:string;label:string;description:string|null;versionNo:number;valueType:string;catalogueId:string|null;status:string};
export type VersionOption={versionId:string;versionNo:number;label:string;description:string|null;reason:string;publishedAt:string};
export class ProfileRequestError extends Error {constructor(public readonly status:number,message:string){super(message);this.name='ProfileRequestError';}}
export async function profileRequest<T>(tenantId:string,path:string,payload?:unknown):Promise<T>{
 const response=await browserFetch(`/api/trade-profiles/${path}`,{method:payload===undefined?'GET':'POST',cache:'no-store',signal:AbortSignal.timeout(35000),headers:{'Content-Type':'application/json','X-Expected-Tenant-Id':tenantId},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
 const result=await response.json();if(!response.ok)throw new ProfileRequestError(response.status,result.error?.message??result.detail??'Trade-profile request failed.');return result as T;
}
