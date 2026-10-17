'use client';
import {useState} from 'react';
import Link from 'next/link';
import {accessLabel} from '@/lib/access-administration';
import {actionTitle} from '@/lib/access-presentation';
import {useAccessData} from './access-loader';
type Matrix={strategies:Array<{strategyId:string;name:string;status:string}>;rows:Array<{userId:string;name:string;strategyId:string;actions:string[];grantSources:Record<string,string[]>}>};
export function StrategyAccessMatrix({initial}:{initial?:Matrix}) {
 const {data,error,reload}=useAccessData<Matrix>('/api/access/strategy-matrix',initial);
 const [selected,setSelected]=useState('');
 const [query,setQuery]=useState('');
 const [filter,setFilter]=useState('all');
 if(!data)return <p role={error?'alert':'status'}>{error||'Loading strategy access…'} {error?<button className="access-secondary" onClick={()=>void reload()}>Retry loading</button>:null}</p>;
 const strategy=data.strategies.find(s=>s.strategyId===selected)??data.strategies[0];
 const rows=data.rows.filter(row=>row.strategyId===strategy?.strategyId);
 const visible=rows.filter(row=>row.name.toLowerCase().includes(query.trim().toLowerCase())&&(filter==='all'||(filter==='allowed'?row.actions.length>0:row.actions.length===0)));
 const allowed=rows.filter(row=>row.actions.length>0).length;
 return <section className="access-matrix">
  <div className="access-section-heading"><div><h2>Who can access this strategy?</h2><p className="muted">Choose a strategy to see each user’s allowed actions and the groups granting them.</p></div><button className="access-secondary" onClick={()=>void reload()}>Refresh access</button></div>
  <p className="access-hint">Administrative metadata only. This view does not grant access to trades or valuations.</p>
  {error?<p role="alert">{error}</p>:null}
  {!strategy?<p className="access-empty">No tenant strategies. Create a strategy before reviewing its access.</p>:<>
   <div className="access-matrix-controls">
    <label>Strategy<select value={strategy.strategyId} onChange={e=>setSelected(e.target.value)}>{data.strategies.map(s=><option key={s.strategyId} value={s.strategyId}>{s.name} · {accessLabel(s.status)}</option>)}</select></label>
    <label>Search users<input type="search" value={query} placeholder="User name" onChange={e=>setQuery(e.target.value)}/></label>
    <label>Access filter<select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All users</option><option value="allowed">With strategy access</option><option value="none">Without strategy access</option></select></label>
   </div>
   <div className="access-summary"><span><strong>{allowed}</strong> with access</span><span><strong>{rows.length-allowed}</strong> without access</span><span role="status">Showing {visible.length} of {rows.length} users</span></div>
   <div className="access-table-scroll"><table className="access-table"><caption className="access-sr-only">Current action grants and their source groups for {strategy.name}</caption><thead><tr><th scope="col">User</th><th scope="col">Strategy actions</th><th scope="col">Access explanation</th></tr></thead><tbody>
    {visible.map(row=><tr key={row.userId}><th scope="row">{row.name}</th><td>{row.actions.length?<div className="access-chips">{row.actions.map(action=><span className="access-action-chip" key={action}>{actionTitle(action)}</span>)}</div>:<span className="access-no-grant">No strategy access</span>}</td><td>
     {row.actions.length?<details><summary>Why this access?</summary><dl className="access-grant-details">{Object.entries(row.grantSources).map(([action,groups])=><div key={action}><dt>{actionTitle(action)}</dt><dd>{groups.join(', ')||'No source group reported'}</dd></div>)}</dl></details>:<p className="access-hint">No effective group grant for this strategy.</p>}
     <Link href={`/tenant-profile/effective-access?userId=${encodeURIComponent(row.userId)}`}>View full user access<span className="access-sr-only"> for {row.name}</span></Link>
    </td></tr>)}
   </tbody></table></div>
   {!visible.length?<p className="access-empty" role="status">No users match these filters. Change the name or access filter.</p>:null}
  </>}
 </section>;
}
