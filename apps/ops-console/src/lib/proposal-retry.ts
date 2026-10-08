export type ProposalRetry={payload:string;key:string};
function canonical(value:unknown):unknown {
  if(Array.isArray(value))return value.map(canonical);
  if(value!==null&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,canonical(item)]));
  return value;
}
/** Retain uncertain-response keys until the form's intent changes or unmounts. */
export function withProposalRetry<T extends object>(payload:T,state:{current:ProposalRetry|null}):T&{idempotencyKey:string} {
  const intent=JSON.stringify(canonical(payload));
  if(state.current?.payload!==intent)state.current={payload:intent,key:crypto.randomUUID()};
  return {...payload,idempotencyKey:state.current.key};
}
