import {browserFetch} from '@/lib/browser-fetch';
export async function reportingRequest<T>(path:string,body?:unknown,key?:string,signal?:AbortSignal):Promise<T>{
 const response=await browserFetch('/api/regulatory-reporting/'+path,{cache:'no-store',signal,
  ...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json',...(key?{'Idempotency-Key':key}:{})},body:JSON.stringify(body)})});
 const data=await response.json();
 if(!response.ok)throw new Error(data.detail??data.error?.message??'Reporting request failed. Reload current state before retrying.');
 return data as T;
}
export function saveFile(name:string,content:string,type:string){
 const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');
 a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
