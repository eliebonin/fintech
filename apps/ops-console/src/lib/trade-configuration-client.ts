import type { components } from "api-contracts";
export type Catalogue=components["schemas"]["CatalogueView"];
export type CatalogueRecord=components["schemas"]["RecordView"];
export type ConfiguredProperty={definitionId:string;code:string;label:string;description:string|null;valueType:string;catalogueId:string|null;required:boolean;versionNo:number;status:"ACTIVE"|"RETIRED"};
export type Selection=components["schemas"]["SelectionView"];
export async function configurationRequest<T>(tenantId:string,path:string,payload?:unknown):Promise<T> {
  const response=await fetch(`/api/trade-configuration/${path}`,{method:payload===undefined?"GET":"POST",cache:"no-store",signal:AbortSignal.timeout(35000),headers:{"Content-Type":"application/json","X-Expected-Tenant-Id":tenantId},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error?.message??result.detail??"Configuration request failed.");
  if(path==='properties'&&payload===undefined&&Array.isArray(result.data)&&result.pagination){
    const {total,limit}=result.pagination;
    if(total>10000)throw new Error('Field history exceeds the alpha display budget. Server-side filtered history is required; no records have been silently omitted.');
    const records=[...result.data];
    while(records.length<total){
      const next=await configurationRequest<ConfiguredProperty[]>(tenantId,`properties?limit=${limit}&offset=${records.length}`);
      if(!next.length)throw new Error('Field history changed while loading. Reload before editing.');
      records.push(...next);
    }
    return records as T;
  }
  return result.data as T;
}
