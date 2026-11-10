import Link from 'next/link';
import {ProfileWorkspace} from './profile-workspace';
import {FieldLibrary} from './field-library';
import {ConfigurationHistory} from './configuration-history';
import {TraderEligibility} from './trader-eligibility';
import styles from './profiles.module.css';
export function TradeConfigurationWorkspace({tenantId,view='profiles',versionId,query}:{tenantId:string;view?:string;versionId?:string;query?:string}){
 const selected=['profiles','fields','history','traders'].includes(view)?view:'profiles';
 return <main className="mvp-page configuration-page"><div className="configuration-workspace"><header className="mvp-header"><div><Link href="/tenant-profile">← Tenant profile</Link><p className="eyebrow">TENANT TRADE GOVERNANCE</p><h1>Trade configuration</h1><p>Maintain shared definitions, publish reusable profiles, then assign an exact version to each strategy.</p></div></header>
 <nav aria-label="Trade configuration" className={styles.nav}>{[['profiles','Profiles'],['fields','Field library'],['history','History']].map(([key,label])=><Link key={key} href={`?view=${key}`} aria-current={selected===key?'page':undefined}>{label}</Link>)}<Link href="/tenant-profile/reference-data">Reference data ↗</Link></nav>
 {selected==='profiles'?<ProfileWorkspace tenantId={tenantId} initialVersionId={versionId}/>:selected==='fields'?<FieldLibrary tenantId={tenantId} initialQuery={query}/>:selected==='traders'?<TraderEligibility tenantId={tenantId}/>:<ConfigurationHistory tenantId={tenantId}/>}
 </div></main>;
}
