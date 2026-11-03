'use client';
import {useEffect,useState} from 'react';
import {readInterest} from './interest-api';

type Resource<T>={key:string;data:T|null;loading:boolean;error:string};
/** A page request cannot erase another dataset or attach old data to a new scope. */
export function useInterestData<T>(path:string|null,revision:number,valid:(value:unknown)=>boolean){
 const key=path===null?'':`${path}#${revision}`;
 const [state,setState]=useState<Resource<T>>({key:'',data:null,loading:false,error:''});
 useEffect(()=>{
  if(!path)return;
  let obsolete=false;const controller=new AbortController();
  setState({key,data:null,loading:true,error:''});
  void readInterest<T>(path,controller.signal).then(data=>{
   if(!valid(data))throw new Error('The service returned incomplete interest records. Refresh this dataset.');
   if(!obsolete)setState({key,data,loading:false,error:''});
  }).catch(cause=>{if(!obsolete)setState({key,data:null,loading:false,error:cause instanceof Error?cause.message:'Records could not be loaded.'});});
  return()=>{obsolete=true;controller.abort();};
 // Validators are stable module-level contract checks, not query dependencies.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[path,revision]);
 return state.key===key?state:{key,data:null,loading:!!path,error:''};
}
