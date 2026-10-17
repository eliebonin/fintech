import {BffApiError} from './api-errors';
export type ProposalRetry={payload:string;key:string};
export function confirmProposalRetry(state:{current:ProposalRetry|null},result:unknown):string{
 const id=(result as {data?:{proposalId?:unknown}}|null)?.data?.proposalId;
 if(typeof id!=='string'||!id)throw new Error('Proposal could not be confirmed. Retry unchanged or inspect Operations.');
 state.current=null;return id;
}
export function rejectProposalRetry(state:{current:ProposalRetry|null},error:unknown):void{
 if(error instanceof BffApiError&&[400,401,403,404,422].includes(error.status))state.current=null;
}
function canonical(value:unknown):unknown {
  if(Array.isArray(value))return value.map(canonical);
  if(value!==null&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,canonical(item)]));
  return value;
}
/** Keep reviewed proposal intent fixed until confirmation or a definite rejection. */
export function withProposalRetry<T extends object>(payload:T,state:{current:ProposalRetry|null}):T&{idempotencyKey:string} {
  const intent=JSON.stringify(canonical(payload));
  if(state.current&&state.current.payload!==intent)throw new Error('An earlier outcome is unknown. Retry unchanged or reconcile the request in Operations before editing.');
  if(!state.current)state.current={payload:intent,key:crypto.randomUUID()};
  return {...payload,idempotencyKey:state.current.key};
}
