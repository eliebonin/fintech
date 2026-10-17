'use client';
import {useCallback,useEffect,useState} from 'react';
import {accessRequest} from '@/lib/access-administration';
import {BffApiError} from '@/lib/api-errors';
export function useAccessData<T>(url:string,initial?:T){
 const [data,setData]=useState<T|undefined>(initial),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [stale,setStale]=useState(false);
 const reload=useCallback(async()=>{try{setData(await accessRequest<T>(url));setError('');setStale(false);return true;}catch(e){setStale(true);setError(e instanceof Error?e.message:'Access data is unavailable.');return false;}},[url]);
 useEffect(()=>{if(initial)return;const controller=new AbortController();accessRequest<T>(url,{signal:controller.signal}).then(setData).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Access data is unavailable.');});return()=>controller.abort();},[url,initial]);
 async function command(path:string,body:unknown,method='POST',headers?:Record<string,string>){
  if(stale)return false;
  setBusy(true);setError('');try{
   await accessRequest(path,{method,body:JSON.stringify(body),headers});
   if(!await reload()){setError('Change saved, but the refreshed state is unavailable. Displayed data is stale. Refresh the list before any further changes; do not submit the saved command again.');return false;}
   return true;
  }catch(e){const rejected=e instanceof BffApiError&&[400,401,403,404,409,422].includes(e.status);setStale(!rejected||[401,403,409].includes((e as BffApiError).status));setError(rejected?e.message:'The change could not be confirmed. Refresh and check the current state before retrying.');return false;}finally{setBusy(false);}
 }
 return {data,error,busy,stale,reload,command,setError,setBusy};
}
