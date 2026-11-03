import {browserFetch} from '@/lib/browser-fetch';
import {parseApiErrorResponse} from '@/lib/api-errors';
import type {InterestIntent} from './interest-types';

export async function readInterest<T>(path:string,signal:AbortSignal):Promise<T>{
 for(let attempt=0;;attempt++){
  signal.throwIfAborted();
  const response=await browserFetch(`/api/valuation/${path}`,{cache:'no-store',signal});
  const delay=Number(response.headers.get('Retry-After')??'1');
  // React development replay can contend with an abandoned read still holding
  // the tenant's workload slot. Only GET is retried, never a financial intent.
  if(response.status===429&&attempt<2&&Number.isFinite(delay)&&delay>=0&&delay<=30){
   await response.body?.cancel();
   await new Promise<void>((resolve,reject)=>{
    if(signal.aborted){reject(signal.reason);return;}
    const abort=()=>{clearTimeout(timer);reject(signal.reason);};
    const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve();},delay*1000);
    signal.addEventListener('abort',abort,{once:true});
   });
   continue;
  }
  if(!response.ok)throw await parseApiErrorResponse(response,'Interest records could not be loaded.');
  return response.json();
 }
}
export async function writeInterest(intent:InterestIntent,key:string):Promise<Record<string,unknown>>{
 const response=await browserFetch(`/api/valuation/${intent.path}`,{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:JSON.stringify(intent.body)});
 if(!response.ok)throw await parseApiErrorResponse(response,'The input could not be saved.');
 const result=await response.json();
 const identity=intent.path==='balance-history-refresh'?'build_id':'input_id';
 const context=intent.path==='balance-history-refresh'?{strategy_id:'strategyId',from_date:'fromDate',to_date:'toDate'}:{strategy_id:'strategyId',instrument_id:'instrumentId',currency_id:'currencyId',value_date:'valueDate'};
 if(!result||typeof result[identity]!=='string'||!result[identity]||Object.entries(context).some(([stored,sent])=>typeof result[stored]!=='string'||result[stored]!==intent.body[sent]))throw new Error('The service returned an incomplete confirmation. The outcome is unknown; retry the original request.');
 return result;
}
