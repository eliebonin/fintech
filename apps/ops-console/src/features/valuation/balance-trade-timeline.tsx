'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {formatTradeExactDecimal} from '@/lib/trades';
import {useInterestData} from './use-interest-data';
import {balanceChartBox,validateBalanceRange} from './balance-chart-model';
import styles from './balance-trade-timeline.module.css';

export type BalanceTradeEvent={tradeId:string;instrumentId:string;balanceDate:string;executionDatetime:string;settlementDate:string|null;
 side:'BUY'|'SELL';signedQuantity:string;quantityUnit:string;tradeAccruedAmount:string|null;currency:string;counterparty:string|null;tradeType:string};
type Scope={strategyId:string;instrumentId:string;from:string;to:string};
type Response={strategyId:string;instrumentId:string;fromDate:string;toDate:string;items:BalanceTradeEvent[];total:number};
const decimal=(value:unknown)=>typeof value==='string'&&/^-?\d+(?:\.\d+)?$/.test(value);
export function validTradeEvents(value:unknown,scope:Scope):value is Response{
 if(!value||typeof value!=='object')return false;
 const data=value as Response,seen=new Set<string>();
 if(data.strategyId!==scope.strategyId||data.instrumentId!==scope.instrumentId||data.fromDate!==scope.from||data.toDate!==scope.to||!Array.isArray(data.items)||data.total!==data.items.length)return false;
 return data.items.every(item=>{
  if(!item||typeof item.tradeId!=='string'||seen.has(item.tradeId)||item.instrumentId!==scope.instrumentId||
   !['BUY','SELL'].includes(item.side)||!decimal(item.signedQuantity)||/^-?0(?:\.0+)?$/.test(item.signedQuantity)||
   (item.side==='SELL')!==item.signedQuantity.startsWith('-')||!(item.tradeAccruedAmount===null||decimal(item.tradeAccruedAmount))||
   typeof item.balanceDate!=='string'||validateBalanceRange(item.balanceDate,item.balanceDate)||item.balanceDate<scope.from||item.balanceDate>scope.to||
   typeof item.executionDatetime!=='string'||!Number.isFinite(Date.parse(item.executionDatetime))||
   !(item.settlementDate===null||typeof item.settlementDate==='string'&&!validateBalanceRange(item.settlementDate,item.settlementDate))||
   typeof item.currency!=='string'||typeof item.quantityUnit!=='string'||typeof item.tradeType!=='string'||!(item.counterparty===null||typeof item.counterparty==='string'))return false;
  seen.add(item.tradeId);return true;
 });
}

/** Group annotations only. Never net transactions or total amounts across currencies. */
export function tradeMarkerGroups(items:BalanceTradeEvent[],from:string,to:string){
 const error=validateBalanceRange(from,to);if(error)throw new Error(error);
 const start=Date.parse(`${from}T00:00:00Z`),end=Date.parse(`${to}T00:00:00Z`),groups=new Map<string,{id:string;date:string;side:'BUY'|'SELL';items:BalanceTradeEvent[];x:number}>();
 for(const item of items){
  if(item.balanceDate<from||item.balanceDate>to)throw new Error('Trade event outside the selected range');
  const id=`${item.balanceDate}:${item.side}`,time=Date.parse(`${item.balanceDate}T00:00:00Z`);
  const x=start===end?(balanceChartBox.left+balanceChartBox.right)/2:balanceChartBox.left+(time-start)/(end-start)*(balanceChartBox.right-balanceChartBox.left);
  if(!groups.has(id))groups.set(id,{id,date:item.balanceDate,side:item.side,items:[],x});
  groups.get(id)!.items.push(item);
 }
 return [...groups.values()].sort((a,b)=>a.id.localeCompare(b.id)).map(group=>({...group,items:group.items.slice().sort((a,b)=>a.executionDatetime.localeCompare(b.executionDatetime)||a.tradeId.localeCompare(b.tradeId))}));
}
const amount=(value:string|null)=>value===null?'Not recorded':formatTradeExactDecimal(value);
const summary=(item:BalanceTradeEvent)=>`${item.side==='BUY'?'Buy':'Sell'} ${amount(item.signedQuantity)} ${item.quantityUnit.toLowerCase()} · traded accrued ${amount(item.tradeAccruedAmount)} ${item.currency} · ${item.counterparty??'Counterparty not recorded'} · executed ${item.executionDatetime} · settlement ${item.settlementDate??'not recorded'}`;

export function BalanceTradeTimeline(scope:Scope){
 const [show,setShow]=useState(true),[selected,setSelected]=useState<string|null>(null),[revision,setRevision]=useState(0);
 const query=new URLSearchParams({strategyId:scope.strategyId,instrumentId:scope.instrumentId,fromDate:scope.from,toDate:scope.to}).toString();
 const resource=useInterestData<Response>(show?`balance-trades?${query}`:null,revision,value=>validTradeEvents(value,scope));
 useEffect(()=>setSelected(null),[query]);
 const groups=tradeMarkerGroups(resource.data?.items??[],scope.from,scope.to),active=groups.find(group=>group.id===selected);
 const label=(group:typeof groups[number])=>`${group.date} · ${group.items.length} ${group.side==='BUY'?'buy':'sell'}${group.items.length===1?'':'s'}`;
 return <section className={styles.timeline} aria-label="Trade events over the balance history">
  <label className={styles.toggle}><input type="checkbox" checked={show} onChange={event=>setShow(event.target.checked)}/>Show trades</label>
  {show&&<><p className={styles.note}>Markers use the balance-impact date. Details show execution and settlement separately.</p>
   {resource.loading?<p role="status">Loading trade markers…</p>:resource.error?<p role="status" className={styles.warning}>Trade markers unavailable: {resource.error} <button type="button" onClick={()=>setRevision(n=>n+1)}>Retry trades</button></p>:
    !groups.length?<p className={styles.note}>No trades in this range.</p>:<>
     <svg className={styles.strip} viewBox={`0 0 ${balanceChartBox.width} 90`} role="group" aria-label="Trade dates: buy and sell markers">
      <text x={balanceChartBox.left-12} y={29} textAnchor="end">Buys ▲</text><text x={balanceChartBox.left-12} y={65} textAnchor="end">Sells ▼</text>
      {[25,61].map(y=><line key={y} x1={balanceChartBox.left} x2={balanceChartBox.right} y1={y} y2={y}/>)}
      {groups.map(group=>{const y=group.side==='BUY'?25:61;return <g key={group.id} role="button" tabIndex={0} aria-label={label(group)} aria-pressed={selected===group.id}
       onMouseEnter={()=>setSelected(group.id)} onFocus={()=>setSelected(group.id)} onClick={()=>setSelected(group.id)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();setSelected(group.id);}}}>
       <title>{`${label(group)}\n${group.items.map(summary).join('\n')}`}</title><rect x={group.x-10} y={y-12} width={20} height={24} className={styles.hit}/>
       <path className={group.side==='BUY'?styles.buy:styles.sell} d={group.side==='BUY'?`M ${group.x} ${y-7} l 6 12 h -12 Z`:`M ${group.x} ${y+7} l 6 -12 h -12 Z`}/>
       {group.items.length>1&&<text x={group.x+9} y={y+4}>{group.items.length}</text>}
      </g>;})}
     </svg>
     {active?<section className={styles.details} aria-label={`Trades on ${active.date}`}><header><h4>{label(active)}</h4><button type="button" aria-label="Close trade details" onClick={()=>setSelected(null)}>×</button></header>
      <ul>{active.items.map(item=><li key={item.tradeId}><Link href={`/trades/${item.tradeId}`}>Open {item.side==='BUY'?'buy':'sell'} trade</Link><span>{amount(item.signedQuantity)} {item.quantityUnit.toLowerCase()} · {item.tradeType.replaceAll('_',' ').toLowerCase()}</span>
       <span>Traded accrued: {amount(item.tradeAccruedAmount)} {item.currency} · {item.counterparty??'Counterparty not recorded'}</span><small>Executed (UTC): {item.executionDatetime} · Settlement: {item.settlementDate??'Not recorded'} · Balance impact: {item.balanceDate}</small></li>)}</ul>
     </section>:<p className={styles.note}>Hover, focus or select a marker to inspect its trades.</p>}
   </>}
   <details className={styles.note}><summary>About trade history</summary>Trades reflect the selected To date and the booking information available when loaded. Stored balances can have older inputs; their source warnings still apply. These markers do not change balances or confirm payments.</details>
  </>}
 </section>;
}
