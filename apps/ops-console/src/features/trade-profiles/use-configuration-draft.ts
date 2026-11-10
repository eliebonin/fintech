'use client';
import {useEffect,type MutableRefObject} from 'react';
/** Unsaved metadata stays local; no browser-storage copy of tenant configuration. */
export function useConfigurationDraft(dirty:MutableRefObject<boolean>){
 useEffect(()=>{
  const url=window.location.href,state=window.history.state;
  const leave=()=>!dirty.current||window.confirm('Discard the unsaved configuration draft?');
  const warn=(event:BeforeUnloadEvent)=>{if(dirty.current){event.preventDefault();event.returnValue='';}};
  const click=(event:MouseEvent)=>{const link=(event.target as Element)?.closest?.('a[href]') as HTMLAnchorElement|null;
   if(link&&link.target!=='_blank'&&!link.hasAttribute('download')&&!link.getAttribute('href')?.startsWith('#')&&!leave()){event.preventDefault();event.stopPropagation();}
  };
  const back=(event:PopStateEvent)=>{if(!leave()){event.stopImmediatePropagation();window.history.pushState(state,'',url);}};
  window.addEventListener('beforeunload',warn);document.addEventListener('click',click,true);window.addEventListener('popstate',back,true);
  return()=>{window.removeEventListener('beforeunload',warn);document.removeEventListener('click',click,true);window.removeEventListener('popstate',back,true);};
 },[dirty]);
}
