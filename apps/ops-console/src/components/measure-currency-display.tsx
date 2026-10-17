'use client';
import {createContext,useContext,useState,type ReactNode} from 'react';
import {formatTradeExactDecimal} from '@/lib/trades';
import {formatMeasureDisplay} from '@/lib/measure-display';
import type {MonetaryMeasure} from './position-measures-report';
export type CurrencyDisplay='local'|'strategy'|'both';
const DisplayContext=createContext<CurrencyDisplay>('both');
/** The server has already authorized and selected both amounts. Display never fetches/reprices. */
export function MeasureCurrencyDisplay({initial,children}:{initial:CurrencyDisplay;children:ReactNode}){
 const [display,setDisplay]=useState(initial);
 return <DisplayContext.Provider value={display}><div className="measure-currency-display"><label>Display amounts<select value={display} onChange={e=>setDisplay(e.target.value as CurrencyDisplay)}><option value="both">Local and strategy currency</option><option value="local">Local currency</option><option value="strategy">Strategy currency</option></select></label>{children}</div></DisplayContext.Provider>;
}
export function MeasureAmount({measure}:{measure:MonetaryMeasure}){
 const display=useContext(DisplayContext);
 if(measure.representation==='CONTRACTUAL_CURRENCY_LEGS'&&measure.legs?.length)return <div className="measure-legs"><small>Contractual currency legs</small>{measure.legs.map(leg=><div key={leg.role}><small>{leg.localAmount==='0'?'Flat':leg.localAmount?.startsWith('-')?'Pay':'Receive'} · {leg.role==='BASE'?'Base':'Quote'}</small><MeasureAmount measure={leg}/></div>)}<small>Undiscounted · not delta or discounted currency exposure</small></div>;
 if(measure.localAmount===null)return <span className={`measure-unavailable ${measure.reasonCode==='NOT_SUPPORTED_YET'?'measure-deferred':''}`}>{measure.reasonCode==='NOT_SUPPORTED_YET'?'Not supported yet':measure.reasonCode==='INVALID_CONTRACT'?'Review required':'Missing required input'}</span>;
 const native=display!=='strategy';
 return <div className="measure-amount">
  {native?<strong title={`${formatTradeExactDecimal(measure.localAmount)} ${measure.currency}`}>{formatMeasureDisplay(measure.localAmount)} {measure.currency}</strong>:null}
  {measure.strategyAmount===null?<small className="measure-warning">Strategy FX unavailable{!native?' · local amount retained in inputs':''}</small>:
   display==='strategy'?<strong title={`${formatTradeExactDecimal(measure.strategyAmount)} ${measure.strategyCurrency}`}>{formatMeasureDisplay(measure.strategyAmount)} {measure.strategyCurrency}</strong>:
   display==='both'&&measure.currency!==measure.strategyCurrency?<small title={`${formatTradeExactDecimal(measure.strategyAmount)} ${measure.strategyCurrency}`}>{formatMeasureDisplay(measure.strategyAmount)} {measure.strategyCurrency}</small>:null}
 </div>;
}
