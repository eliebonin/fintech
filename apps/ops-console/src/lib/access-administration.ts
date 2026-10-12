export type RegistryTenant={tenantId:string;code:string;name:string;status:string;contactName?:string|null;contactEmail?:string|null;profileVersion?:number;moduleCodes:string[];users:Array<{userId:string;name:string;role:string}>};
export type Registry={tenants:RegistryTenant[];modules:Array<{code:string;name:string}>};
export type AccessGroup={groupId:string;code:string;name:string;description:string|null;status:string;actions:string[]};
export type AccessUser={userId:string;name:string;role:string;status:string;accountStatus:string;groupIds:string[];permissions:string[]};
export type TenantAccess={tenantId:string;userId:string;tenantModuleCodes:string[];users:AccessUser[];groups:AccessGroup[];actions:Array<{code:string;moduleCodes:string[]}>};
export function accessLabel(code:string){const value=code.toLowerCase().replaceAll('_',' ');return value.charAt(0).toUpperCase()+value.slice(1);}
export async function accessRequest<T>(url:string,init?:RequestInit):Promise<T>{
 const response=await fetch(url,{...init,cache:'no-store',headers:{'Content-Type':'application/json',...init?.headers}});
 const result=await response.json();
 if(!response.ok)throw new Error(result.error?.message??result.detail??'Access request failed.');
 return result as T;
}
