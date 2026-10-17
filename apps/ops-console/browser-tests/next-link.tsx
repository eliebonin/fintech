// The component harness has no Next router. Link navigation itself is not under
// test here; the separate Next server exercises the real context guard/layout.
import type {AnchorHTMLAttributes} from 'react';
export default function Link(props:AnchorHTMLAttributes<HTMLAnchorElement>){return <a {...props}/>;}
