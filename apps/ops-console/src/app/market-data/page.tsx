import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {WorkspaceShell} from '@/components/workspace-shell';
import {MarketDataNavigation} from '@/components/market-data-navigation';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import type {SourceCatalogue} from '@/lib/market-data-sources';
import styles from '@/components/market-data-workspace.module.css';
export const dynamic='force-dynamic';
export default async function MarketDataPage({searchParams}:{searchParams:Promise<{referenceNodeId?:string;fromDate?:string;toDate?:string;offset?:string;observationOffset?:string}>}){
 const query=await searchParams;
 if(query.referenceNodeId){const params=new URLSearchParams();for(const [key,value] of Object.entries(query))if(value)params.set(key,value);redirect(`/market-data/explorer?${params}`);}
 const access=await resolveWorkspaceAccess();
 if(access.kind==='session-required')redirect('/select-tenant');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace}=access, enabled=workspace.moduleCodes.includes('MARKET_DATA');
 let sources:SourceCatalogue|null=null;
 if(enabled)try{sources=(await(await pricingPolicyClient()).GET('/v1/market-data/sources')).data??null;}catch{/* Explicit metadata unavailability. */}
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><main className="mvp-page">
  {enabled?<MarketDataNavigation active="overview"/>:null}
  <header className="mvp-header"><div><p className="eyebrow">MARKET DATA OPERATIONS</p><h1>Market data overview</h1><p>Find required inputs, investigate gaps and manage the sources and rules used to select prices.</p></div></header>
  {!enabled?<p className="error-panel">ACCESS RESTRICTED: Market data is not enabled. Contact your tenant administrator.</p>:<div className={styles.content}>
   <div className={styles.metrics}>
    <div className={styles.metric}><span>Sources in your access catalogue</span><strong>{sources?sources.sources.length:'Unavailable'}</strong><p>Recorded entitlement metadata; this is not proof of instrument coverage.</p></div>
    <div className={styles.metric}><span>Sources with recorded valuation permissions</span><strong>{sources?sources.sources.filter(s=>s.purposes.includes('VALUATION')&&s.nonDisplayAllowed).length:'Unavailable'}</strong><p>Actual inputs still require policy, freshness and coverage checks.</p></div>
    <div className={styles.metric}><span>Required-input coverage</span><strong>Not checked</strong><p>Choose explicit references, a date and a policy to assess the inputs you need.</p></div>
   </div>
   {!sources?<p role="alert" className="error-panel">Source configuration could not be loaded. Reload to retry; data readiness has not been inferred.</p>:sources.sources.length===0?<p className="configuration-hint">No entitled source datasets are recorded for this tenant. Inspect Sources &amp; access before checking prices.</p>:null}
   <section className={styles.tasks} aria-label="Market data tasks">
    <Link href="/market-data/coverage" className={styles.task}><h2>Check coverage</h2><p>Assess explicitly required inputs and see missing, stale, restricted or unresolved results.</p><span>Choose inputs and check →</span></Link>
    <Link href="/market-data/explorer" className={styles.task}><h2>Investigate an instrument</h2><p>Search recorded series, then open the price history and source evidence you need.</p><span>Open data explorer →</span></Link>
    <Link href="/market-data/sources" className={styles.task}><h2>Sources &amp; access</h2><p>Inspect feed coverage, permitted uses and the effective source priority order.</p><span>Manage sources →</span></Link>
    <Link href="/market-data/policies" className={styles.task}><h2>Pricing setup</h2><p>Configure selection rules and preview inputs. Exchange and strategy calendars determine expected sessions.</p><span>Open pricing policies →</span></Link>
   </section>
   <section className={styles.panel} style={{marginTop:24}}><h2>Ingestion monitoring</h2><p>Delivery activity is not monitored on this overview. Stored observations do not prove a feed is running or that every expected session is present.</p><p>Use coverage checks for required prices and the explorer for recorded observations. No download or backfill starts from this page.</p></section>
  </div>}
 </main></WorkspaceShell>;
}
