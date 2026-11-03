'use client';
import {useEffect,useState} from 'react';
import {formatTradeExactDecimal} from '@/lib/trades';
import {balancePage,type BalancePageSize} from './balance-chart-model';
import type {ClosingBalanceInput,DailyInterestInput,InterestEditor,InterestOptions} from './interest-types';
import styles from './interest-workspace.module.css';

export function InterestSource({reference,children}:{reference?:string;children?:React.ReactNode}){
 return <details className={styles.source}><summary>Source reference</summary><p>{reference||'Retained source evidence'}</p>{children}</details>;
}
export function InterestPagination({size,onSize,offset,count,total,onOffset,disabled=false}:{size:BalancePageSize;onSize:(size:BalancePageSize)=>void;offset:number;count:number;total:number;onOffset:(offset:number)=>void;disabled?:boolean}){
 return <div className={styles.pagination}><label>Rows per page<select value={size} disabled={disabled} onChange={event=>{onSize(event.target.value==='all'?'all':Number(event.target.value) as BalancePageSize);onOffset(0);}}>{[25,50,100].map(n=><option key={n} value={n}>{n}</option>)}<option value="all">All</option></select></label><span aria-live="polite">{total?`${offset+1}–${offset+count} of ${total}`:'0 records'}</span><div className={styles.actions}><button type="button" disabled={disabled||size==='all'||offset===0} onClick={()=>onOffset(Math.max(0,offset-(size as number)))}>Previous</button><button type="button" disabled={disabled||size==='all'||offset+count>=total} onClick={()=>onOffset(offset+(size as number))}>Next</button></div></div>;
}
export function InterestInputTable({kind,rows,options,writable,locked,onEdit}:{kind:'daily'|'closing';rows:(DailyInterestInput|ClosingBalanceInput)[];options:InterestOptions;writable:boolean;locked:boolean;onEdit:(editor:InterestEditor)=>void}){
 const [size,setSize]=useState<BalancePageSize>(25),[offset,setOffset]=useState(0);
 useEffect(()=>setOffset(0),[rows]);
 const page=balancePage(rows,size,offset),daily=kind==='daily';
 return <>
  {!rows.length?<div className={styles.empty}><h3>{daily?'No daily interest in this window':'No closing-balance inputs in this window'}</h3><p>{daily?'Add a sourced earned amount for each date you maintain. Missing entries are not confirmed zero.':'Add a sourced end-of-day accrued balance to establish or reconcile history. This is a stock, not additional income.'}</p></div>:<div className={`pnl-table-scroll ${styles.tableScroll}`}><table className="pnl-table"><caption>{daily?'Validated daily earned-interest inputs':'Sourced closing-balance inputs'} · {rows.length} records</caption><thead><tr><th scope="col">Value date</th><th scope="col">Bond</th><th scope="col">Currency</th><th scope="col" className="pnl-amount">{daily?'Daily earned':'Closing balance'}</th><th scope="col">Revision / status</th><th scope="col">Source</th>{writable&&<th scope="col">Actions</th>}</tr></thead><tbody>{page.items.map(row=>{
   const amount='daily_earned_interest' in row?row.daily_earned_interest:row.closing_balance;
   const name=row.instrument_name??options.bonds.find(bond=>bond.id===row.instrument_id)?.label??'Retained bond';
   const currency=row.currency_code??options.currencies.find(item=>item.id===row.currency_id)?.label??'Retained currency';
   return <tr key={row.input_id}><td>{row.value_date}</td><td>{name}</td><td>{currency}</td><td className="pnl-amount" title={amount??undefined}>{amount===null?'Withdrawn':formatTradeExactDecimal(amount)}</td><td><span className={` ${'status' in row&&row.status==='WITHDRAWN'?styles.muted:styles.badge}`}>{'status' in row&&row.status==='WITHDRAWN'?'Withdrawn':'Validated'} · v{row.revision}</span></td><td><InterestSource reference={'payload' in row?row.payload.sourceReference:row.source_reference}><details><summary>Retained input evidence</summary><pre>{JSON.stringify(row,null,2)}</pre></details></InterestSource></td>{writable&&<td><div className={styles.rowActions}><button type="button" disabled={locked} aria-haspopup="dialog" aria-label={`Correct ${name} on ${row.value_date}`} onClick={()=>onEdit('payload' in row?{kind:'daily',row}:{kind:'closing',row})}>{'status' in row&&row.status==='WITHDRAWN'?'Replace':'Correct'}</button>{'status' in row&&row.status==='ACTIVE'&&<button type="button" disabled={locked} aria-haspopup="dialog" onClick={()=>onEdit({kind:'withdraw',row})} aria-label={`Withdraw ${name} on ${row.value_date}`} className={styles.textDanger}>Withdraw</button>}</div></td>}</tr>;
  })}</tbody></table></div>}
  <InterestPagination size={size} onSize={setSize} offset={page.start} count={page.items.length} total={page.total} onOffset={setOffset} disabled={locked}/>
 </>;
}
