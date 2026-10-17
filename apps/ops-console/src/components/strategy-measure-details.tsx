import Link from 'next/link';
import {formatTradeExactDecimal} from '@/lib/trades';
import type {MeasureRow} from './position-measures-report';

function object(value:unknown):Record<string,unknown>{return value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};}
function text(value:unknown){return typeof value==='string'?value:typeof value==='number'?String(value):'Not recorded';}
const formulas:Record<string,string>={
 SECURITY_PRICE:'Signed quantity × unit multiplier × selected price ÷ quote factor. The three amounts are equal by the agreed cash-security convention.',
 DIRTY_PRICE:'Market value = signed face × dirty price ÷ quote factor. Accrued interest is already included.',
 CLEAN_PLUS_ACCRUED_BALANCE:'Market value = signed face × clean price ÷ quote factor + assessed accrued-interest balance. Daily earnings are not the balance.',
 INCOMPLETE:'Full bond market value needs an eligible dirty mark, or clean mark plus an assessed accrued balance.',
 FUTURE_CURRENT_NOTIONAL:'Reference notional and exposure = canonical contracts × futures price × frozen monetary multiplier ÷ quote factor. This is not contract MTM.',
 FX_FORWARD_CONTRACTUAL_LEGS:'Base leg = signed base amount. Quote leg = −base amount × frozen agreed rate. Each currency is translated separately; no net scalar exposure or discounted MTM is inferred.',
 WHOLE_SWAP_MARK:'Market value = signed units/nominal × whole-swap mark ÷ quote factor. Unit-index exposure also uses the index level, leverage and performance direction; these are not applied to the whole-swap mark again.',
};

export function MeasureDetails({row,strategyId,query,informationCutoff}:{row:MeasureRow;strategyId:string;query:URLSearchParams;informationCutoff:string}){
 const evidence=row.evidence,key=object(evidence.positionKey),selections=object(evidence.selections);
 const movements=new URLSearchParams({view:'positions',asOf:query.get('asOf')??'',basis:query.get('basis')??'EXECUTED',position:row.positionId,informationCutoff});
 const bookingIds=Array.isArray(evidence.bookingTradeIds)?evidence.bookingTradeIds.filter((id):id is string=>typeof id==='string'):[];
 return <div className="measure-detail-content">
  <h3>{row.name} · Inputs and calculation</h3><p>{formulas[evidence.route??'']??'No supported calculation route. Review the retained input explanation.'}</p>
  <details><summary>Exact monetary amounts</summary><dl className="measure-facts">{Object.entries(row.measures).map(([name,measure])=><div className="measure-exact-value" key={name}><dt>{name==='referenceNotional'?'Reference notional':name==='economicExposure'?'Exposure':'Market value'}</dt><dd>{measure.localAmount===null?'No scalar amount':`${formatTradeExactDecimal(measure.localAmount)} ${measure.currency}`}{measure.strategyAmount!==null?<><br/>{formatTradeExactDecimal(measure.strategyAmount)} {measure.strategyCurrency}</>:null}{measure.legs?.map(leg=><p key={leg.role}>{leg.role}: {formatTradeExactDecimal(leg.localAmount)} {leg.currency}{leg.strategyAmount!==null?` · ${formatTradeExactDecimal(leg.strategyAmount)} ${leg.strategyCurrency}`:''}</p>)}</dd></div>)}</dl></details>
  <dl className="measure-facts"><dt>Signed quantity</dt><dd>{formatTradeExactDecimal(row.quantity)} {row.quantityUnit}</dd><dt>Unit / monetary multiplier</dt><dd>{text(key.unit_multiplier)}</dd><dt>Quote divisor</dt><dd>{text(key.quote_factor)}</dd></dl>
  {Object.entries(selections).map(([role,value])=>{const item=object(value),selection=object(item.selection);if(!Object.keys(selection).length&&!item.rate)return null;
   const label=role.replace(/([a-z])([A-Z])/g,'$1 $2');
   return <section key={role} className="measure-input"><h4>{label}</h4><dl className="measure-facts">
    <dt>{item.rate?'Applied FX rate':'Selected price / rate'}</dt><dd>{text(item.rate??selection.valuation_value??selection.selected_value)}</dd>
    <dt>Applied currency</dt><dd>{item.rate?`${text(item.sourceCurrencyCode)} → ${text(item.targetCurrencyCode)}`:text(item.currencyCode)}</dd>
    <dt>{item.rate?'Actual FX date':'Actual price date'}</dt><dd>{text(item.observationDate??selection.pricing_date_used)}</dd>
    {object(item.series).source_system_id?<><dt>Source</dt><dd>{text(object(item.series).source_system_id)}</dd></>:null}
    {item.method?<><dt>Conversion</dt><dd>{text(item.method)}</dd></>:null}
   </dl></section>;
  })}
  {selections.swapTerms?<><h4>Frozen swap conventions</h4><dl className="measure-facts"><dt>Leverage</dt><dd>{text(object(object(selections.swapTerms).terms).leverage)}</dd><dt>Performance direction</dt><dd>{text(object(object(selections.swapTerms).terms).performanceDirection)}</dd><dt>Reference notional per unit</dt><dd>{text(object(object(selections.swapTerms).terms).notionalPerUnit)}</dd></dl></>:null}
  {Array.isArray(selections.forwardContract)&&selections.forwardContract.length?<><h4>Frozen forward agreement</h4><dl className="measure-facts"><dt>Agreed rate</dt><dd>{text(object(object(selections.forwardContract[0]).conventions).agreedRate)}</dd><dt>Quote convention</dt><dd>{text(object(object(selections.forwardContract[0]).conventions).quoteConvention)}</dd><dt>Maturity</dt><dd>{text(object(object(selections.forwardContract[0]).conventions).maturityDate)}</dd></dl></>:null}
  {selections.accruedBalance?<><h4>Assessed accrued balance</h4><p>{formatTradeExactDecimal(text(object(selections.accruedBalance).amount))} {row.measures.marketValue.currency} · {text(object(selections.accruedBalance).valueDate)}</p></>:null}
  {row.measures.economicExposure.legs?<><h4>Contractual local amounts</h4>{row.measures.economicExposure.legs.map(leg=><p key={leg.role}>{leg.role}: {formatTradeExactDecimal(leg.localAmount)} {leg.currency}</p>)}</>:null}
  <Link href={`/strategies/${encodeURIComponent(strategyId)}?${movements}#position-movements`}>View contributing movements</Link>
  {bookingIds.length?<details><summary>Contributing trades ({bookingIds.length})</summary><ul>{bookingIds.map((id,index)=><li key={id}><Link href={`/trades/${encodeURIComponent(id)}`}>Trade {index+1}</Link></li>)}</ul></details>:null}
  <details><summary>Technical evidence · {row.evidenceHash.slice(0,12)}</summary><p>Evidence hash: {row.evidenceHash}</p><pre>{JSON.stringify(evidence,null,2)}</pre></details>
 </div>;
}
