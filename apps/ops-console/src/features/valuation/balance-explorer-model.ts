import {validateBalanceRange} from './balance-chart-model';
import type {BalanceHistoryRow} from './interest-types';
export type BalanceSeries={items:BalanceHistoryRow[];total:number};

/** The chart must receive the complete applied scope, never another instrument or a page. */
export function validBalanceSeries(value:unknown,scope:{instrument:string;from:string;to:string}):value is BalanceSeries{
 if(!value||typeof value!=='object')return false;
 const result=value as BalanceSeries,seen=new Set<string>();
 if(!Array.isArray(result.items)||result.total!==result.items.length)return false;
 return result.items.every(row=>{
  if(!row||typeof row.history_id!=='string'||seen.has(row.history_id)||row.instrument_id!==scope.instrument||
   typeof row.instrument_name!=='string'||typeof row.currency_code!=='string'||!row.currency_code||
   typeof row.basis!=='string'||typeof row.source_status!=='string'||
   typeof row.value_date!=='string'||validateBalanceRange(row.value_date,row.value_date)||row.value_date<scope.from||row.value_date>scope.to)return false;
  seen.add(row.history_id);
  return ['opening_balance','daily_earned','trade_movements','coupon_paid','closing_balance'].every(key=>{
   const amount=row[key as keyof BalanceHistoryRow];return amount===null||typeof amount==='string'&&/^-?\d+(?:\.\d+)?$/.test(amount);
  });
 });
}
