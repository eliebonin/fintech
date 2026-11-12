import {browserFetch} from '@/lib/browser-fetch';
import type {components} from 'api-contracts';
export type Subscription=components['schemas']['SubscriptionView'];
export type SubscriptionPreview=components['schemas']['SubscriptionChangePreview'];
export type Assistance=components['schemas']['AssistanceView'];
export type TransitionPreview=components['schemas']['AssistanceTransitionPreview'];
export type Options=components['schemas']['AssistanceOptions'] & {canConfigureAll?:boolean};
export const tierLabels=['Fully manual','Notifications','Assisted preparation','One-click booking'];
export const events=[{code:'BOND_MATURITY',label:'Bond maturity'},{code:'FX_FORWARD_MATURITY',label:'FX-forward maturity'},{code:'FUTURE_EXPIRY',label:'Futures milestones'},{code:'OPTION_EXPIRY',label:'Option expiry'},{code:'STRUCTURED_OBSERVATION',label:'Structured product schedules'}] as const;
export async function assistanceRequest<T>(path:string,payload?:unknown,tenantId?:string,method='POST'):Promise<T>{
 const response=await browserFetch(path,{method:payload===undefined?'GET':method,cache:'no-store',signal:AbortSignal.timeout(35000),headers:{'Content-Type':'application/json',...(tenantId?{'X-Expected-Tenant-Id':tenantId}:{})},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
 const body=await response.json();if(!response.ok)throw new Error(body.detail??body.error?.message??'Lifecycle assistance could not be loaded.');return body as T;
}
