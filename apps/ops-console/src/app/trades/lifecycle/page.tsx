import Link from 'next/link';
import {redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceShell} from '@/components/workspace-shell';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {BondRedemptionConsole} from '@/components/bond-redemption-console';
import styles from '@/components/bond-redemption-console.module.css';
import {BondCouponConsole} from '@/components/bond-coupon-console';
export const dynamic='force-dynamic';
export default async function LifecyclePage({searchParams}:{searchParams:Promise<{product?:string;strategyId?:string;instrumentId?:string}>}){
 const input=await searchParams,product=input.product;
 const valid=(value:string|undefined)=>value&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)?value:undefined;
 const initialStrategyId=valid(input.strategyId),initialInstrumentId=valid(input.instrumentId);const fx=product==='fx-forward',coupons=product==='coupons';
 const access=await resolveWorkspaceAccess();if(access.kind==='session-required')redirect('/select-context');
 if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
 const {workspace,context}=access;
 return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel="LIFECYCLE OPERATIONS"><main className="mvp-page"><header className={styles.pageHeader}>
  <p><Link href="/lifecycle">← Lifecycle worklist</Link></p><h1>{coupons?'Bond schedules & coupons':fx?'FX-forward maturity closure':'Bond maturity redemption'}</h1>
  <p className={styles.relatedLinks}><Link href="/trades">Trade history</Link> · <Link href="/valuation">Valuation</Link></p>
  <nav className={styles.tabs} aria-label="Lifecycle operation"><Link href="/trades/lifecycle" aria-current={!fx&&!coupons?'page':undefined}>Bond maturity</Link><Link href="/trades/lifecycle?product=fx-forward" aria-current={fx?'page':undefined}>FX forwards</Link><Link href="/trades/lifecycle?product=coupons" aria-current={coupons?'page':undefined}>Bond schedules &amp; coupons</Link></nav>
 </header>{workspace.permissionCodes?.includes('LIFECYCLE_READ')?(coupons?<BondCouponConsole/>:<BondRedemptionConsole tenantId={context.tenantId} key={`${fx?'fx':'bond'}:${initialStrategyId??''}:${initialInstrumentId??''}`} actorId={context.userAccountId} fx={fx} initialStrategyId={initialStrategyId} initialInstrumentId={initialInstrumentId}/>):<p role="alert">Lifecycle read access is required. Ask your administrator to assign explicit strategy-scoped lifecycle permissions in <Link href="/tenant-profile/access?view=groups">Groups</Link>. Admin status alone does not grant them.</p>}</main></WorkspaceShell>;
}
