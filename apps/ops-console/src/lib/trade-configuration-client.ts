import type { components } from "api-contracts";
export type Catalogue=components["schemas"]["CatalogueView"];
export type CatalogueRecord=components["schemas"]["RecordView"];
export type ConfiguredProperty={definitionId:string;code:string;label:string;description:string|null;valueType:string;catalogueId:string|null;required:boolean;versionNo:number;status:"ACTIVE"|"RETIRED"};
export type Selection=components["schemas"]["SelectionView"];
export async function configurationRequest<T>(tenantId:string,path:string,payload?:unknown):Promise<T> {
  const response=await fetch(`/api/trade-configuration/${path}`,{method:payload===undefined?"GET":"POST",cache:"no-store",headers:{"Content-Type":"application/json","X-Expected-Tenant-Id":tenantId},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error?.message??result.detail??"Configuration request failed.");
  return result.data as T;
}
