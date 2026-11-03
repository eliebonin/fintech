import type {components} from 'api-contracts';

export type InstrumentDisplay=components['schemas']['InstrumentDisplayView'];
export type InstrumentDisplays=Record<string,InstrumentDisplay>;

/** Listing identity survives navigation to the canonical instrument's listing row. */
export function instrumentDisplayHref(display:InstrumentDisplay|undefined,referenceId:string,canonicalFallback?:string):string{
 const parent=display?.instrumentId??canonicalFallback??referenceId;
 return `/instruments/${encodeURIComponent(parent)}`+(parent!==referenceId?`#listing-${encodeURIComponent(referenceId)}`:'');
}

export function instrumentIdentifierText(display:InstrumentDisplay):string{
 const id=display.identifier;
 if(!id)return 'Identifier not supplied';
 return ['TICKER','CONTRACT_SYMBOL','TRADING_PAIR','TENANT_REFERENCE'].includes(id.scheme)?id.value:`${id.scheme} ${id.value}`;
}
export function instrumentContextText(display:InstrumentDisplay):string{
 const identifier=display.identifier?.value.trim().toLocaleLowerCase()===display.primaryName.trim().toLocaleLowerCase()?'':instrumentIdentifierText(display);
 return [identifier,...(display.context??[])].filter(Boolean).join(' · ');
}
/** Plain-text equivalent for options and search; never submitted as financial terms. */
export function instrumentDisplayText(display?:InstrumentDisplay,fallbackName?:string):string{
 if(!display)return fallbackName||'Instrument name unavailable';
 return [display.primaryName,instrumentContextText(display)].filter(Boolean).join(' · ');
}
