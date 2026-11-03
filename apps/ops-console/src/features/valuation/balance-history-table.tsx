import Link from 'next/link';
import {formatTradeExactDecimal} from '@/lib/trades';
import type {BalanceHistoryRow} from './interest-types';
const amount=(value:string|null)=>value===null?'Not assessed':formatTradeExactDecimal(value);

export function BalanceHistoryTable({rows,onViewChart,chartDisabled=false,compact=false,snapshotDate}:{rows:BalanceHistoryRow[];onViewChart?:(row:BalanceHistoryRow)=>void;chartDisabled?:boolean;compact?:boolean;snapshotDate?:string}){
 return <div className="pnl-table-scroll"><table className="pnl-table interest-balance-table"><caption>{snapshotDate?`Balances on ${snapshotDate}`:'Maintained local accrued-interest balances'}</caption><thead><tr>
  {!snapshotDate&&<th scope="col" className="interest-date">Date</th>}<th scope="col" className="interest-bond">Bond</th>{onViewChart&&<th scope="col">Chart</th>}<th scope="col">Currency</th><th scope="col" className="pnl-amount">Opening balance</th>{!compact&&<><th scope="col" className="pnl-amount">Daily earned</th><th scope="col" className="pnl-amount">Trade accrual</th><th scope="col" className="pnl-amount">Coupon paid</th></>}<th scope="col" className="pnl-amount">Closing balance</th><th scope="col">Status / evidence</th>
 </tr></thead><tbody>{rows.map(row=><tr key={row.history_id}>
  {!snapshotDate&&<td className="interest-date">{row.value_date}</td>}<td className="interest-bond"><Link href={`/instruments/${row.instrument_id}`}>{row.instrument_name}</Link></td>
  {onViewChart&&<td><button type="button" disabled={chartDisabled} aria-haspopup="dialog" aria-label={`View balance chart for ${row.instrument_name}`} onClick={()=>onViewChart(row)}>View chart</button></td>}
  <td>{row.currency_code}</td>
  {(compact?[row.opening_balance,row.closing_balance]:[row.opening_balance,row.daily_earned,row.trade_movements,row.coupon_paid,row.closing_balance]).map((v,index)=><td key={index} className="pnl-amount" title={v??undefined}>{amount(v)}</td>)}
  <td><span>{row.source_status==='STALE'?'Stale · update required':row.closing_balance===null?'Incomplete':'Current'}</span>
   <details><summary>Balance evidence</summary><p>{row.basis.replaceAll('_',' ').toLowerCase()}</p>{compact&&<dl><dt>Daily earned</dt><dd>{amount(row.daily_earned)}</dd><dt>Trade accrual</dt><dd>{amount(row.trade_movements)}</dd><dt>Coupon paid</dt><dd>{amount(row.coupon_paid)}</dd></dl>}<pre>{JSON.stringify(row.evidence,null,2)}</pre>{row.build_id&&<a href={`/api/valuation/balance-builds/${row.build_id}`} target="_blank" rel="noreferrer">Full build source evidence</a>}</details></td>
 </tr>)}</tbody></table></div>;
}
