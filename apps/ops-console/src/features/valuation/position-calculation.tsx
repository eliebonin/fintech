import type {Item,Presentation} from './types';
import {formatTradeExactDecimal} from '@/lib/trades';
import {FuturesPnlInspection} from './futures-pnl-inspection';
import {BondPriceNormalization} from './bond-price-normalization';

type RecordValue=Record<string,unknown>;
const record=(value:unknown):RecordValue=>value&&typeof value==='object'&&!Array.isArray(value)?value as RecordValue:{};
const records=(value:unknown):RecordValue[]=>Array.isArray(value)?value.filter(row=>row&&typeof row==='object'&&!Array.isArray(row)):[];
const text=(value:unknown)=>typeof value==='string'?value:null;
const decimal=(value:unknown)=>typeof value==='string'&&/^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value)?value:null;
const isZero=(value:unknown)=>typeof value==='string'&&/^[+-]?0+(?:\.0+)?(?:[eE][+-]?\d+)?$/.test(value);
const quotedWrappers=new Set(['ETC','ETN','ETV','ETI','EXCHANGE_TRADED_VEHICLE','EXCHANGE_TRADED_CERTIFICATE']);
type Input={value:string|null;date:string|null;note?:string};
function uniqueInput(inputs:Input[]):Input{
 const unique=[...new Map(inputs.map(input=>[JSON.stringify(input),input])).values()];
 return unique.length===1?unique[0]:{value:null,date:null,note:unique.length?'Multiple recorded inputs · inspect proof':'Not recorded'};
}
function Exact({value,group=false}:{value:unknown;group?:boolean}){const exact=decimal(value);return <span className="pnl-check-exact" title={group?exact??undefined:undefined}>{exact===null?'Not recorded':group?formatTradeExactDecimal(exact):exact}</span>;}
function InputValue({input}:{input:Input}){return input.value?<Exact value={input.value}/>:<span className="pnl-muted">{input.note??'Not recorded'}</span>;}

/** Read frozen inputs/bridge amounts only. Never calculate money, select new data or allocate trade P&L. */
export function PositionCalculation({item,metadata,currency}:{item:Item;metadata:Presentation;currency:string}){
 const data=record(item.evidence),identity=record(data.identity),bucket=record(identity.bucket),key=record(bucket.key);
 const sourceCurrency=text(key.currency_id),targetCurrency=text(identity.reportingCurrency);
 const native=metadata.currencies[sourceCurrency??'']??'Price currency unavailable';
 if(key.product_basis==='FUTURE')return <FuturesPnlInspection item={item} metadata={metadata} currency={currency}/>;
 const reporting=metadata.currencies[targetCurrency??'']??currency;
 const opening=text(identity.openingCutoff)?.slice(0,10),closing=text(identity.closingCutoff)?.slice(0,10);
 const selections=records(data.selections),executions=records(data.executionInputs);
 const noteBases=[...new Set(records(identity.facts).map(f=>text(record(record(f.booking).product_evidence).notePriceType)).filter(Boolean))];
 const sameCurrency=Boolean(sourceCurrency&&targetCurrency&&sourceCurrency===targetCurrency);
 function priceAt(day:string|undefined):Input{
  return uniqueInput(selections.filter(s=>day&&s.valuation_date===day&&(!s.input_role||s.input_role==='PRICE'||s.input_role==='FORWARD_RATE')&&
   (!s.valuation_position_subject_id||s.valuation_position_subject_id===item.subject_id)).map(s=>({
    value:decimal(s.valuation_value)??decimal(record(record(s.pricing_evidence).priceBasis).valuationValue)??decimal(s.selected_value),date:text(s.pricing_date_used)})));
 }
 function fxAt(day:string|undefined):Input{
  if(sameCurrency)return {value:'1',date:null,note:'Same currency · FX = 1'};
  return uniqueInput(selections.filter(s=>day&&s.valuation_date===day&&s.input_role==='FX'&&
   (s.valuation_source_currency_id??record(s.conversion).sourceCurrencyId)===sourceCurrency&&
   (!record(s.conversion).targetCurrencyId||record(s.conversion).targetCurrencyId===targetCurrency)).map(s=>({
    value:decimal(record(s.conversion).rate),date:text(s.pricing_date_used)??text(record(s.conversion).observationDate)})));
 }
 const flowOnly=key.product_basis==='ECONOMIC_FLOW';
 if(flowOnly)return <section className="pnl-manual-check" aria-label="Manual P&L check"><h4>Recorded income / cost</h4>
  <p>This is a dated cash flow, not an investment position. Income-classified amounts use their recorded FX; payment-only entries do not create new P&amp;L.</p>
  <div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Recorded flow inputs · exact values</caption><thead><tr><th scope="col">Economic date</th><th scope="col">Component / recognition</th><th scope="col">Local amount</th><th scope="col">Currency</th><th scope="col">FX to {reporting}</th></tr></thead>
   <tbody>{records(data.economicInputs).filter(input=>input.booking).map((input,index)=>{const booking=record(input.booking),fx=record(input.fx);return <tr key={index}><th scope="row">{text(booking.economicDate)??'Not recorded'}</th><td>{text(booking.component)} · {text(booking.recognitionRole)}</td><td><Exact value={booking.amount} group/></td><td>{metadata.currencies[text(booking.currencyId)??'']??'Not recorded'}</td><td><Exact value={fx.method==='IDENTITY'?'1':fx.rate}/></td></tr>;})}</tbody></table></div>
  <p>For income or costs: local amount × recorded FX; the resulting components are listed below. Payment confirmation alone is not new earnings.</p>
 </section>;
 if(!Object.keys(bucket).length)return <section className="pnl-manual-check" aria-label="Manual P&L check"><h4>Reproduce this P&amp;L</h4><p>Boundary inputs are not recorded in this result version. No quantities, prices or FX rates are inferred. Retained evidence remains available below.</p></section>;
 const prices=[priceAt(opening),priceAt(closing)];
 const closingFx=fxAt(closing),openingFx=isZero(bucket.opening_quantity)?closingFx:fxAt(opening);
 const forward=key.product_basis==='FX_FORWARD';
 const agreedRates=[...new Set(records(identity.facts).map(f=>decimal(record(record(f.booking).product_evidence).agreedRate)).filter((rate):rate is string=>rate!==null))];
 const dates=[...new Set(selections.filter(s=>!s.input_role||s.input_role==='PRICE'||s.input_role==='FORWARD_RATE'||s.input_role==='FX').map(s=>text(s.valuation_date)).filter((day):day is string=>Boolean(day&&opening&&closing&&day>=opening&&day<=closing)))].sort();
 const adjustments=records(data.splitAdjustments);
 return <section className="pnl-manual-check" aria-label="Manual P&L check"><h4>Reproduce this P&amp;L</h4>
  <p>Exact frozen inputs used for this result. Price/FX P&amp;L is separate from interest, resets and costs listed below.</p>
  <div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Boundary prices and quantities</caption><thead><tr><th scope="col">Input</th><th scope="col">Opening · {opening??'date not recorded'}</th><th scope="col">Closing · {closing??'date not recorded'}</th></tr></thead><tbody>
   <tr><th scope="row">Signed quantity</th><td><Exact value={bucket.opening_quantity} group/></td><td><Exact value={bucket.closing_quantity} group/></td></tr>
   <tr><th scope="row">{forward?'Contract rate':'Valuation price'} · {native}</th>{[bucket.opening_quantity,bucket.closing_quantity].map((quantity,index)=><td key={index}>{isZero(quantity)?<span className="pnl-muted">Not needed · zero position</span>:<InputValue input={prices[index]}/>}</td>)}</tr>
   <tr><th scope="row">Actual price / rate date</th>{[bucket.opening_quantity,bucket.closing_quantity].map((quantity,index)=><td key={index}>{isZero(quantity)?'Not applicable':prices[index].date??'Not recorded'}</td>)}</tr>
   <tr><th scope="row">FX · {reporting} per 1 {native}</th><td><InputValue input={openingFx}/>{isZero(bucket.opening_quantity)?<small className="pnl-position-caption">Closing FX used · no opening exposure</small>:null}</td><td><InputValue input={closingFx}/></td></tr>
   <tr><th scope="row">Actual FX date</th><td>{sameCurrency?'Same currency · FX = 1':openingFx.date??'Not recorded'}</td><td>{sameCurrency?'Same currency · FX = 1':closingFx.date??'Not recorded'}</td></tr>
   <tr><th scope="row">Recorded boundary value · {reporting}</th><td><Exact value={identity.openingValue} group/></td><td><Exact value={identity.closingValue} group/></td></tr>
  </tbody></table></div>
  <dl className="pnl-check-conventions"><div><dt>Quantity unit</dt><dd>{text(key.quantity_unit)??'Not recorded'}</dd></div><div><dt>Unit multiplier</dt><dd><Exact value={key.unit_multiplier}/></dd></div><div><dt>Quote divisor</dt><dd><Exact value={key.quote_factor}/></dd></div>{forward?<div><dt>Frozen agreed rate</dt><dd><Exact value={agreedRates.length===1?agreedRates[0]:null}/></dd></div>:null}</dl>
  <div className="pnl-check-formula"><strong>How to check</strong>
   <p>{forward?'Boundary value = signed quantity × (contract rate − agreed rate) × FX.':'Boundary value = signed quantity × unit multiplier ÷ quote divisor × valuation price × FX.'}</p>
   <p>Price/FX P&amp;L = closing value − opening value − signed execution value.</p>
   <dl><div><dt>Signed execution value · {reporting}</dt><dd><Exact value={identity.executionValue} group/></dd></div><div><dt>Recorded price/FX P&amp;L · {reporting}</dt><dd><Exact value={item.market_pnl} group/></dd></div></dl>
   <p className="pnl-muted">These are retained amounts, not a browser recalculation. A sell has a negative execution value; rounding evidence is available below.</p>
  </div>
  {forward?<p>Forward values are undiscounted rate-difference values, not gross currency notional or model MTM. Use the frozen agreed rate above, not a maturity spot suggestion.</p>:null}
  {key.product_basis==='BOND'?<><p>Bond prices used here are clean quotations per 100 nominal. Dirty executions are normalized once using frozen accrued interest; daily earned interest is separate.</p><BondPriceNormalization selections={selections}/></>:null}
  {quotedWrappers.has(String(key.product_basis))?<p>Use this security&apos;s whole quoted price and the frozen listing factors above. Underlying exposure and embedded leverage are not applied again. Distributions and costs enter only through separately recorded economic inputs.</p>:null}
  {key.product_basis==='DIGITAL_ASSET'?<p>Quantity is token units; use this exchange listing&apos;s price at its configured daily cut. Convert the trade quote currency to reporting currency. A stablecoin is not assumed equal to USD. Weekend prices require assessed calendar coverage; staking, forks and margin are separate workflows.</p>:null}
  {key.product_basis==='STRUCTURED_PRODUCT'?<p><strong>Note quotation: {noteBases.length===1?noteBases[0]:'Not recorded / inspect frozen proof'}.</strong> Use the supplied whole-note prices and frozen denomination / divisor above. Underlying returns and embedded leverage are already reflected in the mark. CLEAN quotes may add supplied daily interest and assessed accrued-balance FX; DIRTY / no-separate-accrual quotes do not add that interest again. Recorded coupon income is separate from later payment confirmation.</p>:null}
  {key.product_basis==='SWAP'?<p>Use the whole-swap mark and frozen factors above. Do not apply reference notional or leverage a second time.</p>:null}
  {key.product_basis==='OPTION'?<p>Quantity is contracts. Apply the frozen premium multiplier once, not an additional listing or deliverable multiplier.</p>:null}
  {executions.length?<div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Trades during the period · exact inputs</caption><thead><tr><th scope="col">Economic date / trade</th><th scope="col">Signed quantity</th><th scope="col">Execution price used</th><th scope="col">FX to {reporting}</th></tr></thead><tbody>{executions.map((execution,index)=>{const booking=record(execution.booking),day=text(execution.effective_at)?.slice(0,10),trade=text(booking.trade_id);return <tr key={index}><th scope="row">{trade?<a href={`/trades/${encodeURIComponent(trade)}`}>{day??'Date not recorded'} · {text(booking.quantity)?.startsWith('-')?'Sell / decrease':'Buy / increase'}</a>:day??'Not recorded'}</th><td><Exact value={booking.quantity} group/></td><td><Exact value={booking.price}/></td><td><InputValue input={fxAt(day)}/></td></tr>;})}</tbody></table></div>:<p className="pnl-muted">{Array.isArray(data.executionInputs)?'No trades during this period.':'Period execution details are not recorded.'}</p>}
  {dates.length>2?<><p>Multi-day foreign-currency results sum daily bridges; each execution uses its own economic day&apos;s closing FX. Do not translate every trade at the final day&apos;s rate.</p><div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Daily inputs within the period</caption><thead><tr><th scope="col">Valuation date</th><th scope="col">Price / rate</th><th scope="col">Actual price date</th><th scope="col">FX</th><th scope="col">Actual FX date</th></tr></thead><tbody>{dates.map(day=>{const price=priceAt(day),fx=fxAt(day);return <tr key={day}><th scope="row">{day}</th><td><InputValue input={price}/></td><td>{price.date??'Not recorded'}</td><td><InputValue input={fx}/></td><td>{sameCurrency?'Same currency':fx.date??'Not recorded'}</td></tr>;})}</tbody></table></div></>:null}
  {adjustments.length?<div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Reviewed share adjustments · not trades</caption><thead><tr><th scope="col">Effective date</th><th scope="col">Quantity before</th><th scope="col">Quantity after</th><th scope="col">Ratio</th></tr></thead><tbody>{adjustments.map((adjustment,index)=>{const event=record(adjustment.event);return <tr key={index}><th scope="row">{text(event.effective_date)??'Not recorded'}</th><td><Exact value={adjustment.quantity_before} group/></td><td><Exact value={adjustment.quantity_after} group/></td><td><Exact value={event.ratio}/></td></tr>;})}</tbody></table></div>:null}
 </section>;
}
