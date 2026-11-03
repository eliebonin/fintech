import type {Item} from './types';
import {formatTradeExactDecimal} from '@/lib/trades';
import {displayAmount} from './presentation';
type Day={balance:{value_date:string;opening:string|null;daily_earned:string|null;trade_movements:string|null;coupon_paid:string|null;closing:string|null;basis:string;warnings:string[]};opening_fx:string|null;closing_fx:string|null;amount:string|null;reason:string|null};
type Proof={kind:string;currencyId:string;days:Day[]};
const reasons:Record<string,string>={OPENING_ACCRUED_BALANCE_UNAVAILABLE:'Opening accrued balance unavailable',ACCRUED_BALANCE_FX_UNAVAILABLE:'FX inputs unavailable',NOTE_ASSESSED_BALANCE_NOT_SUPPLIED:'Assessed note balance not supplied',AMBIGUOUS_NOTE_INTEREST_ALLOCATION:'Mixed note quote bases need assessed allocation'};
const amount=(value:string|null)=>value===null?'Unknown':formatTradeExactDecimal(value);
const zero=(value:string|null)=>value!==null&&/^[+-]?0+(?:\.0+)?(?:[eE][+-]?\d+)?$/.test(value);

/** Exact retained monetary facts. No calculation, quantity multiplication or new FX lookup. */
export function AccruedBalanceInspection({item,currencies,currency}:{item:Item;currencies:Record<string,string>;currency:string}){
 const proof=(item.evidence as {economicInputs?:Proof[]}|null)?.economicInputs?.find(value=>value.kind==='ACCRUED_BALANCE_FX');
 if(!proof)return null;
 const local=currencies[proof.currencyId]??'Native currency';
 const stocks=new Map((item.display?.accruedBalanceStocks??[]).filter(row=>row.currencyId===proof.currencyId).map(row=>[row.valueDate,row]));
 return <section className="pnl-manual-check" aria-label="Accrued-interest balance and FX"><h4>Accrued-interest balance &amp; FX</h4>
  <p>Opening and closing stocks are position-level monetary amounts in {local} and {currency}. Coupon receipts reduce the stock; they do not create interest income again.</p>
  <div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Accrued balances · local and reporting currency</caption><thead><tr><th scope="col">Date</th><th scope="col">Opening balance</th><th scope="col">Closing balance</th><th scope="col">Accrued FX P&amp;L · {currency}</th></tr></thead><tbody>
   {proof.days.map(day=>{const stock=stocks.get(day.balance.value_date);return <tr key={day.balance.value_date}><th scope="row">{day.balance.value_date}</th>
    {(['opening','closing'] as const).map(boundary=>{const reported=stock?.[boundary==='opening'?'openingReporting':'closingReporting'];return <td key={boundary} title={day.balance[boundary]??undefined}>{day.balance[boundary]===null?'Unknown':displayAmount(day.balance[boundary])} {local}<small className="pnl-position-caption" title={reported??undefined}>{reported==null?'Reporting stock unavailable':`${displayAmount(reported)} ${currency}`}</small></td>;})}
    <td title={day.amount??undefined}>{day.amount===null?'Not calculated':amount(day.amount)}</td></tr>;})}
  </tbody></table></div>
  <p className="pnl-muted">Reporting stocks use the frozen FX for each boundary. Missing stock or FX leaves only that translation unavailable; no current rate is fetched.</p>
  <details><summary>Daily movements and FX proof</summary>
  <div className="pnl-check-scroll"><table className="pnl-table pnl-check-table"><caption>Daily accrued-interest balance · {local}</caption><thead><tr>
   {['Date','Opening balance','Daily earned','Non-income movements','Coupon received','Closing balance',`Opening FX · ${currency}/${local}`,`Closing FX · ${currency}/${local}`,`Accrued FX P&L · ${currency}`,'Coverage'].map(label=><th scope="col" key={label}>{label}</th>)}
  </tr></thead><tbody>{proof.days.map(day=><tr key={day.balance.value_date}>
   <th scope="row">{day.balance.value_date}</th>
    {[day.balance.opening,day.balance.daily_earned,day.balance.trade_movements,day.balance.coupon_paid,day.balance.closing].map((value,index)=><td key={index} title={value??undefined}>{index===3&&day.balance.basis==='STRUCTURED_NOTE_CLEAN_ASSESSED'&&value===null?'Not separately classified · in movements':amount(value)}</td>)}
   <td>{day.opening_fx??stocks.get(day.balance.value_date)?.openingFx??(zero(day.balance.opening)?'Not needed · zero opening balance':'Unknown')}</td><td>{day.closing_fx??stocks.get(day.balance.value_date)?.closingFx??(zero(day.balance.opening)?'Not needed · zero opening balance':'Unknown')}</td>
   <td title={day.amount??undefined}>{day.amount===null?'Not calculated':amount(day.amount)}</td>
   <td>{day.reason?reasons[day.reason]??day.reason.replaceAll('_',' ').toLowerCase():'Included'}{day.balance.closing===null?<small>Closing stock unassessed</small>:null}{day.balance.basis.startsWith('SUPPLIED')?<small>Assessed balance anchor</small>:null}</td>
  </tr>)}</tbody></table></div>
  <p><strong>Opening accrued balance × (closing FX − opening FX).</strong> FX is {currency} per unit of {local}. Supplied daily interest is a separate component using closing FX.</p>
  </details>
 </section>;
}
