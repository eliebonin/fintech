import Link from 'next/link';
import {instrumentContextText,type InstrumentDisplay} from '@/lib/instrument-display';

/** Flow-only markup: safe in table headings, paragraphs, links and result cards. */
export function InstrumentLabel({display,fallbackName,href}:{display?:InstrumentDisplay;fallbackName?:string;href?:string}){
 const name=display?.primaryName||fallbackName||'Instrument name unavailable';
 return <span className="instrument-label">
  <span className="instrument-label-name">{href?<Link href={href}>{name}</Link>:name}</span>
  {display&&instrumentContextText(display)?<span className="instrument-label-context">{instrumentContextText(display)}</span>:null}
 </span>;
}
