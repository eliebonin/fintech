import Link from 'next/link';
import styles from './market-data-workspace.module.css';
const links=[['overview','/market-data','Overview'],['coverage','/market-data/coverage','Coverage'],['explorer','/market-data/explorer','Data explorer'],['sources','/market-data/sources','Sources & access'],['policies','/market-data/policies','Pricing policies'],['calendars','/market-data/calendars','Calendars']] as const;
export function MarketDataNavigation({active}:{active:typeof links[number][0]}){
 return <nav className={styles.navigation} aria-label="Market data workspace">{links.map(([key,href,label])=><Link key={key} href={href} aria-current={key===active?'page':undefined}>{label}</Link>)}</nav>;
}
