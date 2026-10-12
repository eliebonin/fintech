import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {WorkspaceShell} from '@/components/workspace-shell';
import {MarketDataNavigation} from '@/components/market-data-navigation';
import HistoryPage from '@/features/market-data/history-page';
import {getMarketDataCatalogue,describeMvpError} from '@/lib/mvp-api-client';
import {formatMarketDataValue} from '@/lib/market-data-series';
import type {components} from 'api-contracts';
import styles from '@/components/market-data-workspace.module.css';
export const dynamic='force-dynamic';
type Query={q?:string;asOf?:string;referenceNodeId?:string;seriesId?:string;fromDate?:string;toDate?:string;offset?:string;observationLimit?:string;observationOffset?:string};
export default async function MarketDataExplorerPage({searchParams}:{searchParams:Promise<Query>}){
 const query=await searchParams;
 if(query.referenceNodeId)return HistoryPage({searchParams:Promise.resolve(query)});
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-tenant');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {context,workspace}=access,enabled=workspace.moduleCodes.includes('MARKET_DATA');
 const asOf=query.asOf??new Date().toISOString().slice(0,10),q=(query.q??'').slice(0,250);
 const offset=query.offset&&/^\d+$/.test(query.offset)?Math.min(Number(query.offset),100000):0;
 let catalogue:components['schemas']['MarketDataCatalogueResponse']|null=null,error='';
 if(enabled)try{catalogue=await getMarketDataCatalogue(context,{q,asOf,limit:25,offset});}catch(e){error=describeMvpError(e,'Market data catalogue');}
 function pageLink(value:number){return `/market-data/explorer?${new URLSearchParams({q,asOf,offset:String(value)})}`;}
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page">
  {enabled?<MarketDataNavigation active="explorer"/>:null}
  <header className="mvp-header"><div><p className="eyebrow">MARKET DATA / EXPLORER</p><h1>Data explorer</h1><p>Find a recorded series. Open a series to load its chart, observations and provenance.</p></div></header>
  {!enabled?<p className="error-panel">Market data is not enabled. Contact your tenant administrator.</p>:<div className={styles.content}>
   <form className="date-form" method="get"><label>Search name, reference ID, dataset or price type<input type="search" name="q" maxLength={250} defaultValue={q}/></label><label>Latest stored market date on or before<input type="date" name="asOf" required defaultValue={asOf}/></label><button type="submit">Search series</button></form>
   <p className="muted">Latest stored values are display-permitted observations, not policy-selected valuation inputs. Empty series remain visible. Use <Link href="/market-data/coverage">Coverage</Link> to assess inputs with no recorded series.</p>
   {error?<p role="alert" className="error-panel">{error}</p>:catalogue?<>
    <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>Reference</th><th>Price definition</th><th>Source</th><th>Latest stored date</th><th>Latest stored value</th><th>Inspect</th></tr></thead><tbody>
     {catalogue.data.map(row=><tr key={row.seriesId}><td><strong>{row.referenceNodeName}</strong><small>{row.referenceNodeId}</small></td><td>{row.seriesType}<small>{row.latestValueBasis??'Basis not available'} · {row.closingMethod}</small></td><td>{row.latestDatasetName??row.datasetName??'Not catalogued'}<small>{row.expectedFrequency}</small></td><td>{row.latestMarketDate??'No permitted dated observation'}<small>{row.latestReceivedAt?`Received ${row.latestReceivedAt}`:''}</small></td><td>{row.latestValue===null?'—':formatMarketDataValue(row.latestValue,row.valueType)} {row.currency??''}</td><td><Link href={`/market-data/explorer?${new URLSearchParams({referenceNodeId:row.referenceNodeId,seriesId:row.seriesId,toDate:asOf})}`}>History &amp; evidence</Link><br/><Link href={`/market-data/coverage?${new URLSearchParams({references:row.referenceNodeId,valuationDate:asOf})}`}>Check this input</Link></td></tr>)}
     {!catalogue.data.length?<tr><td colSpan={6}>No matching recorded series. This does not establish whether required inputs are covered.</td></tr>:null}
    </tbody></table></div>
    <nav className={styles.pagination} aria-label="Series pages"><span>{catalogue.data.length?`${offset+1}–${offset+catalogue.data.length}`:'0'} of {catalogue.meta.total??0} recorded series</span>{offset>0?<Link href={pageLink(Math.max(0,offset-25))}>Previous</Link>:null}{offset+25<(catalogue.meta.total??0)?<Link href={pageLink(offset+25)}>Next</Link>:null}</nav>
   </>:null}
  </div>}
 </main></WorkspaceShell>;
}
