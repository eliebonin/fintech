'use client';
import {useCallback,useEffect,useState} from 'react';
import {accessRequest} from '@/lib/access-administration';
export function useAccessData<T>(url:string,initial?:T){
 const [data,setData]=useState<T|undefined>(initial),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const reload=useCallback(async()=>{try{setData(await accessRequest<T>(url));setError('');}catch(e){setError(e instanceof Error?e.message:'Access data is unavailable.');}},[url]);
 useEffect(()=>{if(initial)return;const controller=new AbortController();accessRequest<T>(url,{signal:controller.signal}).then(setData).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Access data is unavailable.');});return()=>controller.abort();},[url,initial]);
 async function command(path:string,body:unknown,method='POST',headers?:Record<string,string>){
  setBusy(true);setError('');try{await accessRequest(path,{method,body:JSON.stringify(body),headers});await reload();return true;}catch(e){setError(e instanceof Error?e.message:'Change failed; refresh before retrying.');return false;}finally{setBusy(false);}
 }
 return {data,error,busy,reload,command,setError,setBusy};
}
