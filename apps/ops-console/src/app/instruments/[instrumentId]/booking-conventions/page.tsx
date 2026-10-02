import {notFound,redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {ProductConventionForm} from '@/components/product-convention-form';
import {ProductFacts} from '@/app/trades/new/product-ticket';
import {getActiveTenantContext,getActiveTenantWorkspace} from '@/lib/tenant-session';
import {getInstrument,MvpApiError} from '@/lib/mvp-api-client';
import {listCurrencies,getProductInstrument} from '@/lib/reference-api-client';
export const dynamic='force-dynamic';
export default async function ConventionPage({params}:{params:Promise<{instrumentId:string}>}){
  const {instrumentId}=await params;let context,workspace;try{[context,workspace]=await Promise.all([getActiveTenantContext(),getActiveTenantWorkspace()]);}catch{redirect('/select-tenant');}
  if(workspace.membershipRole!=='TENANT_ADMIN'||!workspace.moduleCodes.includes('TRADING'))redirect('/instruments');
  let instrument;try{instrument=(await getInstrument(context,instrumentId)).data;}catch(e){if(e instanceof MvpApiError&&e.status===404)notFound();throw e;}
  const kind=instrument.instrumentType;if(kind!=='STRUCTURED_PRODUCT'&&kind!=='FUTURE'&&kind!=='BOND')notFound();
  const shell={tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try{const [currencies,terms]=await Promise.all([listCurrencies(context,['REGULAR','CRYPTO']),getProductInstrument(context,instrumentId,new URLSearchParams())]);return <WorkspaceShell {...shell}><main className="mvp-page"><h1>Booking conventions</h1><h2>{instrument.canonicalName}</h2><p>Tenant-owned instruments only. Submit a sourced convention for Operations approval; existing approved versions and booked trades remain immutable.</p><ProductFacts terms={terms.data} configuration/>{terms.data.convention?.kind==='FUTURE'&&terms.data.convention.priceBasis!=='INDEX_POINTS'?<p className="configuration-impact">This contract is creation-only. Crypto futures trade booking, convention amendments and delivery processing are deferred.</p>:<ProductConventionForm kind={kind} currencies={currencies.data} tenantId={context.tenantId} instrumentId={instrumentId} currencyCode={instrument.baseCurrency} current={terms.data.convention}/>}</main></WorkspaceShell>;}catch{return <WorkspaceShell {...shell}><main className="mvp-page"><h1>Booking conventions</h1><p role="alert">Instrument conventions or currency catalogue unavailable. Try again when the service is available.</p></main></WorkspaceShell>;}
}
