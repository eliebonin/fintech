'use client';
import Link from 'next/link';
import {useState} from 'react';
import type {Strategy} from '@/app/strategies/strategy-console';

export function StrategyRegister({strategies,canCreate}:{strategies:Strategy[];canCreate:boolean}){
 const [search,setSearch]=useState(''),[status,setStatus]=useState('ACTIVE'),[type,setType]=useState(''),[page,setPage]=useState(0);
 const rows=strategies.filter(s=>(!status||s.status===status)&&(!type||s.strategyType===type)&&`${s.strategyCode} ${s.displayName}`.toLowerCase().includes(search.toLowerCase()));
 const pages=Math.max(1,Math.ceil(rows.length/25)),current=Math.min(page,pages-1);
 return <main className="mvp-page strategy-workspace">
  <header className="mvp-header"><div><p className="eyebrow">TENANT STRATEGY REGISTER</p><h1>Strategies</h1><p className="muted">Explore the strategies you can read in this tenant.</p></div>{canCreate?<Link className="strategy-primary" href="/strategies/new">Create strategy</Link>:null}</header>
  <section className="strategy-card"><div className="strategy-toolbar"><label>Find a strategy<input type="search" placeholder="Name or code" value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/></label><label>Status<select value={status} onChange={e=>{setStatus(e.target.value);setPage(0);}}><option value="ACTIVE">Active</option><option value="ARCHIVED">Archived</option><option value="">All statuses</option></select></label><label>Type<select value={type} onChange={e=>{setType(e.target.value);setPage(0);}}><option value="">All types</option>{Array.from(new Set(strategies.map(s=>s.strategyType))).sort().map(t=><option key={t}>{t}</option>)}</select></label></div>
  <p className="muted">{rows.length} accessible strategies match. Access is controlled by your tenant groups.</p>
  <div className="table-wrap"><table><caption className="sr-only">Accessible strategies</caption><thead><tr><th>Strategy</th><th>Code</th><th>Type</th><th>Base currency</th><th>Status</th></tr></thead><tbody>{rows.slice(current*25,current*25+25).map(s=><tr key={s.strategyId}><td><Link href={`/strategies/${s.strategyId}`}><strong>{s.displayName}</strong></Link></td><td>{s.strategyCode}</td><td>{s.strategyType.replaceAll('_',' ')}</td><td>{s.baseCurrencyCode??'Not set'}</td><td>{s.status}</td></tr>)}</tbody></table></div>
  {!rows.length?<p className="strategy-empty">No accessible strategies match these filters.</p>:null}<nav className="strategy-paging" aria-label="Strategy pages"><button disabled={current===0} onClick={()=>setPage(current-1)}>Previous</button><span>Page {current+1} of {pages}</span><button disabled={current+1>=pages} onClick={()=>setPage(current+1)}>Next</button></nav></section>
 </main>;
}
