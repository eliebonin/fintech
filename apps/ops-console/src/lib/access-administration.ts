import {browserFetch as fetch} from '@/lib/browser-fetch';
import {parseApiErrorResponse} from './api-errors';
export type RegistryTenant={tenantId:string;code:string;name:string;status:string;contactName?:string|null;contactEmail?:string|null;profileVersion?:number;moduleCodes:string[];users:Array<{userId:string;name:string;role:string}>};
export type Registry={tenants:RegistryTenant[];modules:Array<{code:string;name:string}>};
export type AccessGroup={groupId:string;code:string;name:string;description:string|null;status:string;actions:string[];scopeMode?:'ALL'|'SELECTED';strategyIds?:string[];versionNo?:number};
export type AccessUser={userId:string;name:string;role:string;status:string;accountStatus:string;groupIds:string[];permissions:string[]};
export type TenantAccess={tenantId:string;userId:string;tenantModuleCodes:string[];users:AccessUser[];groups:AccessGroup[];strategies?:Array<{strategyId:string;name:string;status:string}>;actions:Array<{code:string;moduleCodes:string[]}>};
export type AccessExplanation={code:string;moduleCodes:string[];allowed:boolean;grantSources:string[];blockers:string[];strategyNames?:string[]};
export type EffectiveAccess={tenantId:string;userId:string;name:string;role:string;accountStatus:string;membershipStatus:string;asOfDate:string;strategyScope:string;
 groups:Array<{groupId:string;name:string;status:string;actions:string[]}>;
 actions:AccessExplanation[];modules:Array<{code:string;name:string;enabled:boolean;accessible:boolean;deliveryStatus:string;deliveryNote:string;actions:AccessExplanation[]}>};
export function accessLabel(code:string){const value=code.toLowerCase().replaceAll('_',' ');return value.charAt(0).toUpperCase()+value.slice(1);}
export async function accessRequest<T>(url:string,init?:RequestInit):Promise<T>{
 const response=await fetch(url,{...init,cache:'no-store',headers:{'Content-Type':'application/json',...init?.headers}});
 if(!response.ok)throw await parseApiErrorResponse(response,'Access request failed.');
 return await response.json() as T;
}
