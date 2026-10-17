import type {components} from 'api-contracts';
import {browserFetch} from '@/lib/browser-fetch';
import {parseApiErrorResponse} from '@/lib/api-errors';

export type OrganisationDetail=components['schemas']['OrganisationDetail'];
export type OrganisationPage=components['schemas']['OrganisationPage'];
export type OrganisationRole='COUNTERPARTY'|'EXECUTING_BROKER';
export const roles:Record<OrganisationRole,string>={COUNTERPARTY:'Counterparties',EXECUTING_BROKER:'Executing brokers'};
export function isOrganisationDetail(value:OrganisationDetail|OrganisationPage['policies']):value is OrganisationDetail{
 return typeof value.organisationId==='string';
}

export async function organisationRequest<T>(tenantId:string,path:string,payload?:unknown):Promise<T>{
 const response=await browserFetch(`/api/trade-configuration/${path}`,{
  method:payload===undefined?'GET':'POST',cache:'no-store',signal:AbortSignal.timeout(payload===undefined?10000:35000),
  headers:{'Content-Type':'application/json','X-Expected-Tenant-Id':tenantId},
  ...(payload===undefined?{}:{body:JSON.stringify(payload)})});
 if(!response.ok)throw await parseApiErrorResponse(response,'Organisation request failed.');
 const result=await response.json();const data=result?.data;
 const validPolicies=(value:unknown)=>!!value&&typeof value==='object'&&Object.keys(roles).every(r=>{
  const p=(value as Record<string,{mode?:unknown;versionNo?:unknown}>)[r];
  return p&&['CURATED','LEGACY'].includes(String(p.mode))&&Number.isInteger(p.versionNo);});
 const validRow=(value:unknown)=>{
  if(!value||typeof value!=='object')return false;
  const row=value as OrganisationDetail;
  return typeof row.organisationId==='string'&&typeof row.displayName==='string'&&typeof row.legalName==='string'
   &&typeof row.status==='string'&&Array.isArray(row.leis)&&row.leis.every(lei=>typeof lei==='string')
   &&Number.isInteger(row.versionNo)&&row.versionNo>=0
   &&[row.label,row.internalCode,row.notes].every(text=>text===null||typeof text==='string')
   &&Object.keys(roles).every(r=>typeof row.roles?.[r as OrganisationRole]==='boolean');
 };
 const valid=path.startsWith('organisation-roles/')?validPolicies(data)
  :path==='organisations'||path.startsWith('organisations?')||path.startsWith('organisations/candidates')
   ?data&&Array.isArray(data.items)&&data.items.every(validRow)&&Number.isInteger(data.total)&&validPolicies(data.policies)
   :validRow(data)&&data.organisationId===path.split('/').pop()&&validPolicies(data.policies)&&Array.isArray(data.history);
 if(!valid)throw new Error('The response could not be confirmed. Retry the unchanged request or reload current state.');
 return data as T;
}

export function saveBody(detail:OrganisationDetail,form:FormData){
 const text=(name:string)=>String(form.get(name)??'').trim()||null;
 return {expectedVersion:detail.versionNo,
  expectedRoleVersions:Object.fromEntries(Object.keys(roles).map(r=>[r,detail.policies[r as OrganisationRole].versionNo])),
  label:text('label'),internalCode:text('internalCode'),notes:text('notes'),reason:text('reason'),
  roles:Object.fromEntries(Object.keys(roles).filter(r=>detail.policies[r as OrganisationRole].mode==='CURATED')
   .map(r=>[r,form.get(r)==='on']))};
}
