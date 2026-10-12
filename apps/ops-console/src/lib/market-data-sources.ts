import type {components} from 'api-contracts';
export type SourceCatalogue=components['schemas']['SourceCatalogueView'];
export type SourcePriority=components['schemas']['PriorityView'];
export type SourceCommand=components['schemas']['SourcePriorityInput'];

export function moveSource(order:string[],id:string,direction:-1|1):string[]{
 const index=order.indexOf(id), next=index+direction;
 if(index<0||next<0||next>=order.length)return [...order];
 const result=[...order];[result[index],result[next]]=[result[next],result[index]];return result;
}
export function initialOrder(sources:{datasetId:string;tenantOwned:boolean}[],saved:string[]|null):string[]{
 return saved!==null?[...saved]:[...sources].sort((a,b)=>Number(b.tenantOwned)-Number(a.tenantOwned)).map(source=>source.datasetId);
}
