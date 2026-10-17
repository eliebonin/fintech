'use client';

import type {ReactNode} from 'react';

/** Panels stay mounted so switching tasks cannot discard unsaved input or evidence. */
export function WorkspaceTabs({id,label,items,value,onChange}:{id:string;label:string;items:{id:string;label:string}[];value:string;onChange:(id:string)=>void}) {
 return <div className="workspace-tabs" role="tablist" aria-label={label}>
  {items.map((item,index)=><button key={item.id} type="button" role="tab" id={`${id}-tab-${item.id}`} aria-controls={`${id}-panel-${item.id}`} aria-selected={value===item.id} tabIndex={value===item.id?0:-1} onClick={()=>onChange(item.id)} onKeyDown={event=>{
   const next=event.key==='Home'?0:event.key==='End'?items.length-1:event.key==='ArrowRight'?(index+1)%items.length:event.key==='ArrowLeft'?(index+items.length-1)%items.length:null;
   if(next===null)return;
   event.preventDefault();onChange(items[next].id);
   event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
  }}>{item.label}</button>)}
 </div>;
}

export function WorkspaceTabPanel({id,tab,value,children}:{id:string;tab:string;value:string;children:ReactNode}) {
 return <section className="workspace-tab-panel" role="tabpanel" id={`${id}-panel-${tab}`} aria-labelledby={`${id}-tab-${tab}`} hidden={value!==tab} tabIndex={0}>{children}</section>;
}

function focusTarget(id:string){document.getElementById(id)?.focus();}

export function WorkspaceSkipLink(){
 return <a className="workspace-skip-link" href="#workspace-content" onClick={()=>focusTarget('workspace-content')}>Skip to page content</a>;
}

export function WorkspaceOutline({items}:{items:{id:string;label:string}[]}){
 return <nav className="workspace-outline" aria-label="On this page"><span>On this page</span>{items.map(item=><a key={item.id} href={`#${item.id}`} onClick={()=>focusTarget(item.id)}>{item.label}</a>)}</nav>;
}
