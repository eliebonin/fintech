import type {Item,Presentation} from './types';
import {formatTradeExactDecimal} from '@/lib/trades';
type Execution={tradeId:string;quantity:string;price:string;effectiveAt:string};
type Day={valueDate:string;openingDate:string;openingQuantity:string;closingQuantity:string;openingPrice:string|null;closingPrice:string|null;monetaryMultiplier:string;quoteFactor:string;localVariation:string;closingFx:string;reportingVariation:string;executions:Execution[]};
type Proof={kind:string;currencyId:string;days:Day[];contractConvention?:{priceBasis:string;settlementMethod:string;contractSize?:string|number|null;lastTradingAtUtc:string;finalSettlementDate:string;deliveryStartDate?:string|null;deliveryEndDate?:string|null}};
const exact=(value:string|null)=>value===null?'Not required · zero contracts':formatTradeExactDecimal(value);

/** Frozen server inputs only: neither a browser pricer nor a contract-MTM view. */
export function FuturesPnlInspection({item,metadata,currency}:{item:Item;metadata:Presentation;currency:string}){
 const proof=(item.evidence as {economicInputs?:Proof[]}|null)?.economicInputs?.find(value=>value.kind==='FUTURES_DAILY_VARIATION');
 if(!proof)return <p className="pnl-notice">Futures variation inputs unavailable. Inspect retained technical evidence.</p>;
 const local=metadata.currencies[proof.currencyId]??'Price currency';
 const selections=(item.evidence as {selections?:{valuation_date:string;pricing_date_used?:string;input_role?:string;valuation_source_currency_id?:string}[]}).selections??[];
 const actual=(date:string,fx=false)=>selections.find(s=>s.valuation_date===date&&(fx?s.input_role==='FX'&&s.valuation_source_currency_id===proof.currencyId:!s.input_role||s.input_role==='PRICE'))?.pricing_date_used??'Not recorded';
 return <section className="pnl-manual-check" aria-label="Manual futures P&L check"><h4>Futures daily P&amp;L</h4>
  <p>Opening contracts use the preceding boundary price; trades use their execution prices. Apply the monetary multiplier and quote divisor once, then the economic day&apos;s closing FX. Margin cash is assessed separately from cash balances.</p>
  <p className="pnl-muted">These are recorded price-variation amounts. Gross futures notional is not an asset value; contract MTM is not assessed here.</p>
  {proof.contractConvention?<><dl className="pnl-fact-grid"><div><dt>Quotation</dt><dd>{proof.contractConvention.priceBasis==='UNDERLYING_UNIT'?'Underlying-unit quote':'Index points'}</dd></div><div><dt>Settlement</dt><dd>{proof.contractConvention.settlementMethod==='PHYSICAL'?'Physical delivery':'Cash settlement'}</dd></div><div><dt>Final settlement date</dt><dd>{proof.contractConvention.finalSettlementDate}</dd></div>{proof.contractConvention.settlementMethod==='PHYSICAL'?<><div><dt>First delivery date</dt><dd>{proof.contractConvention.deliveryStartDate??'Not recorded'}</dd></div><div><dt>Last delivery date</dt><dd>{proof.contractConvention.deliveryEndDate??'Not recorded'}</dd></div></>:null}</dl><p className="pnl-muted">No cash or underlying delivery is posted by this calculation. Actual closure and delivery remain separate Ops records.</p></>:null}
  {proof.days.map(day=><article key={day.valueDate}><h5>{day.openingDate} → {day.valueDate}</h5>
   <div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Exact futures inputs · {local}</caption><thead><tr><th scope="col">Input</th><th scope="col">Opening</th><th scope="col">Closing</th></tr></thead><tbody>
    <tr><th scope="row">Signed contracts</th><td>{exact(day.openingQuantity)}</td><td>{exact(day.closingQuantity)}</td></tr>
    <tr><th scope="row">Contract price</th><td>{exact(day.openingPrice)}</td><td>{exact(day.closingPrice)}</td></tr>
    <tr><th scope="row">Actual price date</th><td>{day.openingPrice===null?'Not required':actual(day.openingDate)}</td><td>{day.closingPrice===null?'Not required':actual(day.valueDate)}</td></tr>
   </tbody></table></div>
   <dl className="pnl-fact-grid">{[['Monetary multiplier',day.monetaryMultiplier],['Quote divisor',day.quoteFactor],[`Price variation · ${local}`,day.localVariation],[`Closing FX · ${currency} per 1 ${local}`,day.closingFx],[`Futures P&L · ${currency}`,day.reportingVariation]].map(([label,value])=><div key={label}><dt>{label}</dt><dd title={value}>{exact(value)}</dd></div>)}</dl>
   <p className="pnl-muted">Actual FX date: {actual(day.valueDate,true)}. Same-currency conversion uses identity FX without an observation.</p>
   {day.executions.length?<div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Trades in this bridge</caption><thead><tr><th scope="col">Trade</th><th scope="col">Signed contracts</th><th scope="col">Execution price</th></tr></thead><tbody>{day.executions.map(execution=><tr key={execution.tradeId}><th scope="row"><a href={`/trades/${encodeURIComponent(execution.tradeId)}`}>{execution.effectiveAt.slice(0,10)} · {execution.quantity.startsWith('-')?'Sell':'Buy'}</a></th><td>{exact(execution.quantity)}</td><td>{exact(execution.price)}</td></tr>)}</tbody></table></div>:<p>No period trades in this bridge.</p>}
  </article>)}
  <p><strong>Local variation = (closing contracts × closing price − opening contracts × opening price − signed execution price amounts) × multiplier ÷ quote divisor.</strong> Convert each day&apos;s variation at its closing FX. Settlement prices follow the selected policy; this view does not post margin cash.</p>
 </section>;
}
