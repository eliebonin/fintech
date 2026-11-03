'use client';
import {useState,type FormEvent} from 'react';
import Link from 'next/link';
import {PagedValuationChoice} from './paged-choice';
import {useInterestData} from './use-interest-data';
import {BalanceSeriesReport} from './balance-history-chart';
import {validateBalanceRange} from './balance-chart-model';
import {validBalanceSeries,type BalanceSeries} from './balance-explorer-model';
import type {InterestOptions} from './interest-types';
import styles from './interest-workspace.module.css';
import explorer from './balance-explorer.module.css';

type Props={initialStrategy:string;initialInstrument:string;initialFrom:string;initialTo:string};
type Scope={strategy:string;instrument:string;from:string;to:string;strategyLabel?:string};
const validOptions=(value:unknown)=>!!value&&Array.isArray((value as InterestOptions).bonds)&&(value as InterestOptions).bonds.every(bond=>
 typeof bond.id==='string'&&typeof bond.label==='string'&&typeof bond.currency==='string');

export function BalanceExplorer({initialStrategy,initialInstrument,initialFrom,initialTo}:Props){
 const initial={strategy:initialStrategy,instrument:initialInstrument,from:initialFrom,to:initialTo};
 const [form,setForm]=useState(initial),[scope,setScope]=useState<Scope|null>(initialStrategy&&initialInstrument&&!validateBalanceRange(initialFrom,initialTo)?initial:null);
 const [search,setSearch]=useState(''),[error,setError]=useState(''),[revision,setRevision]=useState(0),[optionRevision,setOptionRevision]=useState(0),[currency,setCurrency]=useState('');
 const options=useInterestData<InterestOptions>(form.strategy?`interest-options?${new URLSearchParams({strategyId:form.strategy})}`:null,optionRevision,validOptions);
 const query=scope?new URLSearchParams({strategyId:scope.strategy,instrumentId:scope.instrument,fromDate:scope.from,toDate:scope.to}).toString():'';
 const series=useInterestData<BalanceSeries>(scope?`balance-series?${query}`:null,revision,value=>!!scope&&validBalanceSeries(value,scope));
 const bonds=options.data?.bonds??[],chosen=bonds.find(bond=>bond.id===form.instrument);
 const filtered=bonds.filter(bond=>`${bond.label} ${bond.currency} ${bond.id}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
 const choices=chosen&&!filtered.some(bond=>bond.id===chosen.id)?[chosen,...filtered]:filtered;
 const currencies=Array.from(new Set(series.data?.items.map(row=>row.currency_code)??[])).sort();
 const activeCurrency=currencies.includes(currency)?currency:currencies[0]??'';
 const rows=series.data?.items.filter(row=>row.currency_code===activeCurrency)??[];
 const changed=!!scope&&(form.strategy!==scope.strategy||form.instrument!==scope.instrument||form.from!==scope.from||form.to!==scope.to);
 const reviewQuery=new URLSearchParams({...(scope?.strategy||form.strategy?{strategyId:scope?.strategy||form.strategy}:{}),valueDate:scope?.to||form.to}).toString();
 function apply(event:FormEvent<HTMLFormElement>){
  event.preventDefault();setError('');
  const fields=new FormData(event.currentTarget);
  const requested={strategy:String(fields.get('strategy')??''),instrument:String(fields.get('instrument')??''),from:String(fields.get('fromDate')??''),to:String(fields.get('toDate')??'')};
  const invalid=validateBalanceRange(requested.from,requested.to);
  if(invalid){setError(invalid);return;}
  if(requested.strategy!==form.strategy||!options.data?.bonds.some(bond=>bond.id===requested.instrument)){setError('Choose an instrument available in this strategy.');return;}
  setForm(requested);setScope({...requested,strategyLabel:options.data.strategyLabel});setRevision(n=>n+1);setCurrency('');
  const params=new URLSearchParams({strategyId:requested.strategy,instrumentId:requested.instrument,fromDate:requested.from,toDate:requested.to});
  window.history.replaceState(window.history.state,'',`/valuation/interest/explorer?${params}`);
 }
 return <section className={`pnl-workspace interest-register ${styles.workspace}`} aria-label="Accrued-balance explorer">
  <nav className={styles.tabs} aria-label="Interest workspace"><Link href={`/valuation/interest?${reviewQuery}`}>Daily accrual review</Link><Link href={`/valuation/interest/balances?${reviewQuery}`}>Balance review</Link><Link href="/valuation/interest/explorer" aria-current="page">Explore balances</Link></nav>
  <form className={styles.filters} onSubmit={apply}>
   <div className={explorer.filters}>
    <PagedValuationChoice kind="strategies" label="Strategy" name="strategy" value={form.strategy} initialChoices={[]} required emptyLabel="Choose a strategy"
     onChange={event=>{setForm({...form,strategy:event.target.value,instrument:''});setSearch('');}}/>
    <div className="pnl-paged-choice"><label>Search instrument<input type="search" maxLength={250} placeholder="Name or identifier" value={search} onChange={event=>setSearch(event.target.value)} disabled={!form.strategy||options.loading}/></label>
     <label>Instrument<select name="instrument" required value={form.instrument} disabled={!options.data||options.loading} onChange={event=>setForm({...form,instrument:event.target.value})}>
      <option value="">Choose an instrument</option>{choices.map(bond=><option key={bond.id} value={bond.id}>{bond.label} · {bond.currency}</option>)}
     </select></label><small>{options.loading?'Loading strategy instruments…':`${filtered.length} matching instruments`}</small></div>
    <label>From date<input name="fromDate" type="date" required value={form.from} onInput={event=>setForm({...form,from:event.currentTarget.value})} onChange={event=>setForm({...form,from:event.target.value})}/></label>
    <label>To date<input name="toDate" type="date" required value={form.to} onInput={event=>setForm({...form,to:event.currentTarget.value})} onChange={event=>setForm({...form,to:event.target.value})}/></label>
   </div>
   <div className={styles.filterFooter}><p className={styles.context}>Read-only stored history. Daily review is not a prerequisite.</p><button className={styles.primary} type="submit" disabled={!chosen||options.loading}>Show history</button></div>
   {options.error&&<p role="alert" className={styles.error}>{options.error} <button type="button" onClick={()=>setOptionRevision(n=>n+1)}>Retry instruments</button></p>}{error&&<p role="alert" className={styles.error}>{error}</p>}
  </form>
  {changed&&<p role="status" className={styles.notice}>Filters changed. Choose Show history to apply them; the report below still shows the previous selection.</p>}
  {!scope?<p className={styles.empty}>Choose a strategy, instrument and date range, then Show history.</p>:
   series.loading?<p role="status">Loading the full balance history…</p>:
   series.error?<p role="alert" className={styles.error}>{series.error} <button type="button" onClick={()=>setRevision(n=>n+1)}>Retry history</button></p>:
   series.data?<section className={styles.panel} aria-label="Applied balance history">
    <header className={styles.heading}><div><h2>{series.data.items[0]?.instrument_name??'No stored history in this range'}</h2>
     <p>{scope.strategyLabel??(scope.strategy===form.strategy?options.data?.strategyLabel:'Selected strategy')} · {scope.from} to {scope.to}</p></div>
     {currencies.length>1&&<label>Balance currency<select value={activeCurrency} onChange={event=>setCurrency(event.target.value)}>{currencies.map(code=><option key={code}>{code}</option>)}</select></label>}
    </header>
    <BalanceSeriesReport key={`${query}:${revision}:${activeCurrency}`} rows={rows} from={scope.from} to={scope.to} currency={activeCurrency} tradeScope={{strategyId:scope.strategy,instrumentId:scope.instrument}}/>
   </section>:null}
 </section>;
}
