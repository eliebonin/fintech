'use client';
import {useEffect} from 'react';
/** Pending financial payloads deliberately stay in memory, not browser storage. */
export function useRetainedNavigation(...intents:Array<{current:unknown}>):void{
 useEffect(()=>{
  const unresolved=()=>intents.some(intent=>intent.current!==null&&intent.current!==undefined);
  const leave=()=>window.confirm('A request outcome is unknown. Leaving may lose its retry key. Reconcile history before creating another request. Leave this page?');
  const url=window.location.href,state=window.history.state;
  const warn=(event:BeforeUnloadEvent)=>{if(unresolved()){event.preventDefault();event.returnValue='';}};
  const click=(event:MouseEvent)=>{const link=(event.target as Element)?.closest?.('a[href]') as HTMLAnchorElement|null;
   if(!unresolved()||!link||link.target==='_blank'||link.hasAttribute('download')||link.getAttribute('href')?.startsWith('#'))return;
   if(!leave()){event.preventDefault();event.stopPropagation();}
  };
  const back=(event:PopStateEvent)=>{if(unresolved()&&!leave()){event.stopImmediatePropagation();window.history.pushState(state,'',url);}};
  window.addEventListener('beforeunload',warn);document.addEventListener('click',click,true);window.addEventListener('popstate',back,true);
  return()=>{window.removeEventListener('beforeunload',warn);document.removeEventListener('click',click,true);window.removeEventListener('popstate',back,true);};
 },[]);
}
