import {BffApiError} from './api-errors';

export type RetainedIntent={signature:string;key:string;inFlight?:boolean};
/** One exact JSON intent survives transport/server uncertainty. No automatic replay. */
export async function submitRetained<T,R>(body:T,state:{current:RetainedIntent|null},send:(body:T,key:string)=>Promise<R>):Promise<R>{
 const signature=JSON.stringify(body);
 if(state.current?.inFlight)throw new Error('This request is already being submitted.');
 if(state.current&&state.current.signature!==signature)throw new Error('The previous outcome is unknown. Retry the unchanged request or reconcile it in history before starting a different request.');
 const intent=state.current??{signature,key:crypto.randomUUID()};state.current=intent;intent.inFlight=true;
 try{const result=await send(JSON.parse(intent.signature) as T,intent.key);state.current=null;return result;}
 catch(error){
  // Timeouts, throttling, conflicts and malformed success bodies need reconciliation.
  if(error instanceof BffApiError&&[400,401,403,404,422].includes(error.status))state.current=null;
  throw error;
 }finally{intent.inFlight=false;}
}
