'use client';
import {useEffect,useRef,useState} from 'react';
import {browserFetch} from '@/lib/browser-fetch';
import type {TradeBookingContext} from '@/lib/browser-api-client';

/** Context follows the selected strategy; entered financial values remain owned by the ticket. */
export function useStrategyTradeContext(initial:TradeBookingContext,strategyId:string,corrects?:string){
 const [loaded,setLoaded]=useState<{strategyId:string;context:TradeBookingContext}>();
 const [error,setError]=useState(''),[refresh,setRefresh]=useState(0),[loading,setLoading]=useState(false);
 const sequence=useRef(0);
 useEffect(()=>{
  const serial=++sequence.current;setError('');
  if(!strategyId){setLoaded(undefined);setLoading(false);return;}
  setLoading(true);
  browserFetch(`/api/trades/booking-context?strategyId=${encodeURIComponent(strategyId)}${corrects?`&corrects=${encodeURIComponent(corrects)}`:""}`,{cache:'no-store',headers:{'X-Expected-Tenant-Id':initial.tenantId},signal:AbortSignal.timeout(35000)})
   .then(async response=>{const result=await response.json();if(!response.ok)throw new Error(result.error?.message??result.detail??'Trade configuration could not be loaded.');if(result.data.tenantId!==initial.tenantId||result.data.bookedByUserAccountId!==initial.bookedByUserAccountId||result.data.tradeProfile?.strategyId!==strategyId)throw new Error('Trade configuration context changed. Reload before reviewing.');return result.data as TradeBookingContext;})
   .then(context=>{if(serial===sequence.current)setLoaded({strategyId,context});})
   .catch(caught=>{if(serial===sequence.current)setError(caught instanceof Error?caught.message:'Trade configuration unavailable.');})
   .finally(()=>{if(serial===sequence.current)setLoading(false);});
  return()=>{sequence.current++;};
 },[initial.tenantId,initial.bookedByUserAccountId,strategyId,corrects,refresh]);
 const context=loaded?.strategyId===strategyId?loaded.context:{...initial,properties:[],tradeProfile:null};
 return {context,ready:!!strategyId&&!loading&&!error&&loaded?.strategyId===strategyId,error,loading,reload:()=>setRefresh(n=>n+1)};
}

export function TradeProfileStatus({state}:{state:ReturnType<typeof useStrategyTradeContext>}){
 if(state.loading)return <p role="status">Loading strategy trade configuration…</p>;
 if(state.error)return <div role="alert"><p>{state.error}</p><button type="button" onClick={state.reload}>Reload trade configuration</button><p>Your entered execution details have been retained.</p></div>;
 const profile=state.context.tradeProfile;
 return <p className="muted">{profile?<>Trade configuration: <strong>{profile.profileLabel} · v{profile.versionNo}</strong> <button type="button" onClick={state.reload}>Reload trade configuration</button></>:'Select a strategy to load its standard and custom fields.'}</p>;
}
