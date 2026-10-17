'use client';

import {useId,useState,type ReactNode} from 'react';

/** Only disclosure state crosses the client boundary; all financial output is server-rendered. */
export function MeasureRowDisclosure({name,children,details}:{name:string;children:ReactNode;details:ReactNode}){
 const [open,setOpen]=useState(false);const id=useId();
 return <><tr>{children}<td><button type="button" className="measure-inspect-button" aria-expanded={open} aria-controls={id} onClick={()=>setOpen(!open)}>{open?'Hide':'Inspect'}<span className="sr-only"> {name}</span></button></td></tr>
  <tr id={id} hidden={!open} className="measure-expanded-row"><td colSpan={7}>{details}</td></tr></>;
}
