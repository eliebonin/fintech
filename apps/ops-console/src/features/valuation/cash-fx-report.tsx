import {useRef,useState,type RefObject} from 'react';
import {ValuationPriceEvidence} from '@/components/valuation-price-evidence';
import type {Batch,Presentation} from './types';
import {TechnicalReference} from './technical-reference';
import {displayAmount,componentLabel} from './presentation';

type Snapshot={cash_balance_id:string;amount:string;balance_as_of_date:string;revision:number;source_reference?:string|null;note?:string|null};
type Day={value_date:string;opening:Snapshot;closing:Snapshot;opening_fx:string|null;closing_fx:string|null;amount:string;fx_mode:string};
type CashEvidence={cashFx?:{days:Day[];missing?:unknown[]};selections?:unknown[]};

/** Cash-owned frozen evidence only; never infer flows or calculate P&L in React. */
export function CashFxReport({batch,currency,metadata,componentCodes,headingRef}:{batch:Batch;currency:string;metadata:Presentation;componentCodes?:string[];headingRef:RefObject<HTMLHeadingElement|null>}){
 const [selected,setSelected]=useState<string|null>(null);
 const inspectorHeading=useRef<HTMLHeadingElement>(null);
 const coverage=batch.summary.cashCoverage;
 const all=batch.items.filter(item=>item.cash_account_id);
 if(!coverage&&!all.length)return null;
 const rows=componentCodes?.length?all.filter(item=>componentCodes.some(code=>Object.hasOwn(item.components,code))):all;
 const name=(id:string)=>metadata.cashAccounts?.[id]??'Cash account name unavailable';
 const currencyName=(id:string)=>metadata.currencies[id]??'Currency name unavailable';
 const current=rows.find(row=>row.attribution_id===selected)??rows[0];
 const evidence=current?.evidence as CashEvidence|undefined;
 return <section className="pnl-surface pnl-cash-report" aria-label="Cash FX attribution">
  <div className="pnl-panel-heading"><h3 ref={headingRef} tabIndex={-1}>Cash FX attribution</h3><span>Whole-result cash FX · {displayAmount(batch.summary.cashFxPnl??undefined)} {currency}</span></div>
  <p className="pnl-muted">Opening signed cash × daily FX change. Intraday movements are treated at closing FX, not new income. Accounts remain separate; this is not intraday cash accounting or full NAV.</p>
  {coverage&&coverage.missingCount>0?<details className="pnl-cash-coverage"><summary>Cash coverage · {coverage.missingCount} missing daily scope inputs</summary><p>{coverage.suppliedCount} supplied daily scope inputs. Missing is not zero; only supplied complete daily pairs contribute. Earlier cash history does not create an expected balance today.</p>
   <ul>{coverage.missing.map((m,index)=><li key={index}>{m.valueDate} · {name(m.accountId)} · {currencyName(m.currencyId)} · missing {m.missingOpening&&m.missingClosing?'opening and closing':m.missingOpening?'opening':'closing'} snapshot</li>)}</ul></details>:null}
  {coverage?.status==='NOT_ASSESSED'?<p className="pnl-muted">No cash snapshots supplied for this valuation window.</p>:null}
  <p className="pnl-muted">{rows.length} matching of {all.length} cash account/currency attributions. Source filtering does not change headline totals.</p>
  {rows.length?<div className="pnl-table-scroll"><table className="pnl-table"><caption>Cash account FX P&amp;L · {currency}</caption><thead><tr><th scope="col">Company / account</th><th scope="col">Cash currency</th><th scope="col">Cash FX P&amp;L</th><th scope="col">Total incl. adjustments</th><th scope="col">Inspect</th></tr></thead><tbody>{rows.map(item=><tr key={item.attribution_id} className={item.attribution_id===current?.attribution_id?'pnl-selected':''}><th scope="row">{name(item.cash_account_id!)}<small className="pnl-position-caption">Cash-owned attribution · v{item.version}</small></th><td>{currencyName(item.cash_currency_id!)}</td>
    <td className="pnl-amount" title={item.components.CASH_FX}>{displayAmount(item.components.CASH_FX)}</td><td className="pnl-amount" title={item.net_pnl}>{displayAmount(item.net_pnl)}</td><td><button type="button" aria-pressed={item.attribution_id===current?.attribution_id} onClick={()=>{setSelected(item.attribution_id);requestAnimationFrame(()=>inspectorHeading.current?.focus());}}>Inspect cash inputs</button></td></tr>)}</tbody></table></div>:<p>No recorded cash attribution matches this view. See coverage above; no confirmed zero is inferred from missing inputs.</p>}
  {current?<section className="pnl-cash-inspector pnl-inspector" aria-label="Cash input inspection">
     <h4 ref={inspectorHeading} tabIndex={-1}>{name(current.cash_account_id!)} · {currencyName(current.cash_currency_id!)}</h4>
     <div className="pnl-table-scroll"><table className="pnl-table"><caption>Daily cash FX contributions · {currency}</caption><thead><tr><th scope="col">Value date</th><th scope="col">Opening cash · {currencyName(current.cash_currency_id!)}</th><th scope="col">Closing cash · {currencyName(current.cash_currency_id!)}</th><th scope="col">Opening / closing FX</th><th scope="col">Exact FX P&amp;L · {currency}</th></tr></thead><tbody>{evidence?.cashFx?.days.map(day=><tr key={day.value_date}><th scope="row">{day.value_date}<small>{day.fx_mode==='IDENTITY'?'Same-currency identity':day.fx_mode==='ZERO_OPENING_EXPOSURE'?'Zero opening exposure; FX not required':'Policy-selected daily FX'}</small></th><td>{day.opening.amount}<small>As of {day.opening.balance_as_of_date} · revision {day.opening.revision}</small><TechnicalReference id={day.opening.cash_balance_id} label="Opening cash snapshot ID"/><small>{day.opening.source_reference} {day.opening.note}</small></td><td>{day.closing.amount}<small>As of {day.closing.balance_as_of_date} · revision {day.closing.revision}</small><TechnicalReference id={day.closing.cash_balance_id} label="Closing cash snapshot ID"/><small>{day.closing.source_reference} {day.closing.note}</small></td><td>{day.opening_fx??'Not required'} / {day.closing_fx??'Not required'}</td><td className="pnl-amount">{day.amount}</td></tr>)}</tbody></table></div>
     <ValuationPriceEvidence evidence={current.evidence} metadata={metadata} kind="cash"/>
     <dl className="pnl-fact-grid">{Object.entries(current.components).map(([code,amount])=><div key={code}><dt>{componentLabel(code)} · {currency}</dt><dd>{amount}</dd></div>)}</dl>
     <TechnicalReference id={current.cash_account_id} label="Cash account ID"/><TechnicalReference id={current.attribution_id} label="Attribution ID"/>
     <details><summary>Frozen cash evidence (JSON)</summary><pre>{JSON.stringify(current.evidence,null,2)}</pre></details>
    </section>:null}
  <a href="/valuation/cash-balances">Open cash input register</a>
 </section>;
}
