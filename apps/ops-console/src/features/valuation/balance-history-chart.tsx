'use client';
import {useEffect,useId,useMemo,useRef,useState,type FormEvent,type KeyboardEvent} from 'react';
import {browserFetch} from '@/lib/browser-fetch';
import {parseApiErrorResponse} from '@/lib/api-errors';
import {formatTradeExactDecimal} from '@/lib/trades';
import {BalanceHistoryTable} from './balance-history-table';
import {BalanceTradeTimeline} from './balance-trade-timeline';
import {balanceChartGeometry,balanceChartBox,balancePage,validateBalanceRange,type BalancePageSize} from './balance-chart-model';
import type {BalanceHistoryRow,BalanceChartBond} from './interest-types';
import styles from './balance-history-chart.module.css';

export function BalanceSeriesReport({rows,from,to,currency,tradeScope}:{rows:BalanceHistoryRow[];from:string;to:string;currency:string;tradeScope?:{strategyId:string;instrumentId:string}}){
 const id=useId(),[pageSize,setPageSize]=useState<BalancePageSize>(25),[offset,setOffset]=useState(0),[selected,setSelected]=useState<BalanceHistoryRow|null>(null);
 const [chartType,setChartType]=useState<'line'|'bar'>('line');
 useEffect(()=>{setOffset(0);setSelected(null);},[rows,from,to,currency]);
 const geometry=useMemo(()=>{try{return balanceChartGeometry(rows,from,to);}catch{return null;}},[rows,from,to]);
 const page=balancePage(rows,pageSize,offset),unknown=rows.filter(row=>row.closing_balance===null).length,stale=rows.filter(row=>row.source_status==='STALE').length;
 const label=(row:BalanceHistoryRow)=>`${row.value_date}: ${formatTradeExactDecimal(row.closing_balance!)} ${currency}${row.source_status==='STALE'?' · stale source':''}`;
 const box=balanceChartBox;
 function movePoint(event:KeyboardEvent<SVGSVGElement>){
  if(!geometry?.points.length||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();const last=geometry.points.length-1,current=geometry.points.findIndex(point=>point.row.history_id===selected?.history_id);
  const next=event.key==='Home'?0:event.key==='End'?last:event.key==='ArrowRight'?Math.min(last,current+1):current<0?last:Math.max(0,current-1);
  setSelected(geometry.points[next].row);
 }
 return <section className={styles.report} aria-label="Balance evolution and datapoints">
  <figure className={styles.figure}>
   <figcaption className={styles.chartHeading}><div><h3>Closing accrued balance · {currency}</h3><p>{from} to {to} · {rows.length} stored datapoints{unknown?` · ${unknown} not assessed`:''}</p></div><label className={styles.chartType}>Chart type<select aria-label="Chart type" value={chartType} onChange={event=>setChartType(event.target.value as 'line'|'bar')}><option value="line">Line</option><option value="bar">Bar</option></select></label></figcaption>
   {stale>0&&<p className={styles.warning}>Historical amounts include stale sources ({stale} datapoints). Update balance history before relying on them for a new valuation.</p>}
   {!rows.length?<p>No stored balance datapoints in this window. Choose other dates or update the balance history.</p>:!geometry?<p role="alert">Chart values could not be plotted safely. Exact stored amounts remain in the table below.</p>:!geometry.points.length?<p>No assessed closing balances to plot. Missing balances remain unassessed in the table below.</p>:<>
    <svg className={styles.svg} viewBox={`0 0 ${box.width} ${box.height}`} role="img" tabIndex={0} onKeyDown={movePoint} aria-labelledby={`${id}-title ${id}-description`}>
     <title id={`${id}-title`}>{`Daily closing accrued-interest balance in ${currency}`}</title>
     <desc id={`${id}-description`}>{chartType==='line'?'The line shows stored closing balances across the selected dates. Missing days and unassessed balances break the line; they are not zero.':'Each bar shows a stored closing balance, extending from zero. Negative balances extend below zero; a short marker represents a known zero. Missing days and unassessed balances have no bar; they are not zero.'} Orange marks identify stale source evidence. Focus the chart and use left/right arrows, Home or End to inspect amounts. Exact datapoints and evidence are in the table below.</desc>
     {geometry.ticks.map((tick,index)=><g key={index}><line data-zero-reference={tick.value===0?'true':undefined} className={tick.value===0?styles.zeroLine:styles.grid} x1={box.left} x2={box.right} y1={tick.y} y2={tick.y}/><text className={tick.value===0?styles.zeroLabel:undefined} x={box.left-10} y={tick.y+4} textAnchor="end">{new Intl.NumberFormat('en-GB',{notation:Math.abs(tick.value)>=1e6?'compact':'standard',maximumFractionDigits:2}).format(tick.value)}</text></g>)}
     {chartType==='bar'?<>
      {geometry.bars.map(({row,x,y,width,height})=><g key={row.history_id} onMouseEnter={()=>setSelected(row)} onClick={()=>setSelected(row)}>
       <title>{label(row)}</title><rect data-balance-bar="" className={`${styles.bar} ${row.source_status==='STALE'?styles.stalePoint:styles.point} ${selected?.history_id===row.history_id?styles.selectedBar:''}`} x={x} y={y} width={width} height={height}/>
       {height===0&&<line className={row.source_status==='STALE'?styles.staleZero:styles.knownZero} x1={x} x2={x+width} y1={geometry.zeroY} y2={geometry.zeroY}/>}
      </g>)}
     </>:<>{geometry.segments.map((path,index)=><path key={index} className={styles.line} d={path}/>)}
     {geometry.points.map(({row,x,y})=><g key={row.history_id} onMouseEnter={()=>setSelected(row)} onClick={()=>setSelected(row)}>
      <title>{label(row)}</title><circle className={styles.hit} cx={x} cy={y} r={9}/><circle className={`${row.source_status==='STALE'?styles.stalePoint:styles.point} ${selected?.history_id===row.history_id?styles.selectedPoint:''}`} cx={x} cy={y} r={3}/>
     </g>)}</>}
     {geometry.dates.map((tick,index)=><text key={tick.date} x={tick.x} y={box.height-26} textAnchor={index===0?'start':index===geometry.dates.length-1?'end':'middle'}>{tick.date}</text>)}
    </svg>
    <p className={styles.readout} aria-live="polite">{selected?label(selected):`Hover or tap a ${chartType==='bar'?'bar':'point'}, or focus the chart and use the arrow keys to inspect exact balances.`}</p>
   </>}
   {tradeScope&&<BalanceTradeTimeline {...tradeScope} from={from} to={to}/>}
   <p className={styles.help}>Missing dates are not interpolated. Chart coordinates are illustrative; the table retains exact decimal amounts and source evidence.</p>
  </figure>
  <h3>All stored datapoints</h3>
  {page.items.length>0&&<BalanceHistoryTable rows={page.items}/>}
  <div className="pnl-pagination">
   <label>Datapoints per page<select value={pageSize} onChange={event=>{setPageSize(event.target.value==='all'?'all':Number(event.target.value) as BalancePageSize);setOffset(0);}}>
    {[25,50,100].map(value=><option key={value} value={value}>{value}</option>)}<option value="all">All</option>
   </select></label>
   <button type="button" disabled={pageSize==='all'||page.start===0} onClick={()=>setOffset(Math.max(0,page.start-(pageSize as number)))}>Previous</button>
   <span aria-live="polite">{page.total?`${page.start+1}–${page.start+page.items.length} of ${page.total}`:'0 datapoints'}</span>
   <button type="button" disabled={pageSize==='all'||page.start+page.items.length>=page.total} onClick={()=>setOffset(page.start+(pageSize as number))}>Next</button>
  </div>
 </section>;
}

export function BalanceHistoryViewer({strategyId,bonds,initialBondId,from,to,onClose}:{strategyId:string;bonds:BalanceChartBond[];initialBondId?:string;from:string;to:string;onClose:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null),id=useId();
 const [instrument,setInstrument]=useState(bonds.some(bond=>bond.id===initialBondId)?initialBondId!:bonds[0]?.id||''),[range,setRange]=useState({from,to}),[revision,setRevision]=useState(0);
 const [rows,setRows]=useState<BalanceHistoryRow[]>([]),[currency,setCurrency]=useState(''),[loading,setLoading]=useState(false),[error,setError]=useState('');
 useEffect(()=>{const node=dialog.current;if(node&&!node.open)node.showModal();return()=>{if(node?.open)node.close();};},[]);
 useEffect(()=>{
  let obsolete=false;const controller=new AbortController();setRows([]);setError('');
  if(!instrument){setLoading(false);return;}
  const invalid=validateBalanceRange(range.from,range.to);if(invalid){setError(invalid);setLoading(false);return;}
  setLoading(true);
  const query=new URLSearchParams({strategyId,instrumentId:instrument,fromDate:range.from,toDate:range.to});
  void (async()=>{
   try{
    const response=await browserFetch(`/api/valuation/balance-series?${query}`,{cache:'no-store',signal:controller.signal});
    if(!response.ok)throw await parseApiErrorResponse(response,'Balance chart could not be loaded.');
    const result=await response.json();if(!Array.isArray(result.items)||result.items.length!==result.total)throw new Error('The balance series response is incomplete.');
    if(!obsolete){setRows(result.items);setCurrency(result.items[0]?.currency_code??bonds.find(bond=>bond.id===instrument)?.currency??'');}
   }catch(cause){if(!obsolete)setError(cause instanceof Error?cause.message:'Balance chart could not be loaded.');}
   finally{if(!obsolete)setLoading(false);}
  })();
  return()=>{obsolete=true;controller.abort();};
 },[strategyId,instrument,range.from,range.to,revision,bonds]);
 const currencies=Array.from(new Set(rows.map(row=>row.currency_code))).sort();
 const selectedRows=useMemo(()=>rows.filter(row=>row.currency_code===currency),[rows,currency]);
 function dismiss(){dialog.current?.close();onClose();}
 function apply(event:FormEvent<HTMLFormElement>){event.preventDefault();const data=new FormData(event.currentTarget),from=String(data.get('fromDate')??''),to=String(data.get('toDate')??'');
  const invalid=validateBalanceRange(from,to);if(invalid){setError(invalid);return;}setRange({from,to});setRevision(value=>value+1);
 }
 return <dialog ref={dialog} className={`${styles.dialog} pnl-workspace interest-register`} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`} onCancel={event=>{event.preventDefault();dismiss();}}>
  <header className={styles.heading}><div><h2 id={`${id}-title`}>Accrued-balance evolution</h2><p id={`${id}-description`}>Inspect one bond’s stored closing balances and exact daily datapoints.</p></div><button type="button" className={styles.close} aria-label="Close balance chart" onClick={dismiss}>×</button></header>
  <form className={styles.filters} onSubmit={apply}>
   <label>Bond<select value={instrument} onChange={event=>setInstrument(event.target.value)} autoFocus><option value="">Choose a bond</option>{bonds.map(bond=><option key={bond.id} value={bond.id}>{bond.label} · {bond.currency}</option>)}</select></label>
   <label>From date<input name="fromDate" type="date" required defaultValue={from}/></label><label>To date<input name="toDate" type="date" required defaultValue={to}/></label>
   <button type="submit" disabled={!instrument}>Show chart</button>
  </form>
  {currencies.length>1&&<label>Balance currency<select value={currency} onChange={event=>setCurrency(event.target.value)}>{currencies.map(code=><option key={code}>{code}</option>)}</select></label>}
  {loading?<p role="status">Loading the full balance series…</p>:error?<p role="alert">{error} <button type="button" onClick={()=>setRevision(value=>value+1)}>Retry chart</button></p>:!instrument?<p>Choose a bond to inspect its history.</p>:<BalanceSeriesReport rows={selectedRows} from={range.from} to={range.to} currency={currency}/>}
 </dialog>;
}
