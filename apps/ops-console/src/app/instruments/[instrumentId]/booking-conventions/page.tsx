import { WorkspacePageHeader } from "@/components/workspace-page-header";
import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
import {notFound,redirect} from 'next/navigation';
import {WorkspaceShell} from '@/components/workspace-shell';
import {ProductConventionForm} from '@/components/product-convention-form';
import {ProductFacts} from '@/app/trades/new/product-ticket';
import {getInstrument,MvpApiError} from '@/lib/mvp-api-client';
import {listCurrencies,getProductInstrument} from '@/lib/reference-api-client';
export const dynamic='force-dynamic';
import {canManageInstruments} from '@/lib/instrument-authority';
export default async function ConventionPage({params}:{params:Promise<{instrumentId:string}>}){
  const {instrumentId}=await params;let context,workspace;const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  context = access.context; workspace = access.workspace;
  if(!canManageInstruments(workspace))return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}>{null}</WorkspaceShell>;
  let instrument;try{instrument=(await getInstrument(context,instrumentId)).data;}catch(e){if(e instanceof MvpApiError&&e.status===404)notFound();throw e;}
  const kind=instrument.instrumentType;if(kind!=='STRUCTURED_PRODUCT'&&kind!=='FUTURE'&&kind!=='BOND'&&kind!=='SWAP')notFound();
  const shell={tenantName:workspace.tenantName,membershipRole:workspace.membershipRole,moduleCodes:workspace.moduleCodes};
  try{const [currencies,terms]=await Promise.all([listCurrencies(context,['REGULAR','CRYPTO']),getProductInstrument(context,instrumentId,new URLSearchParams())]);return <WorkspaceShell {...shell}><main className="mvp-page"><WorkspacePageHeader title="Booking conventions" eyebrow="INSTRUMENTS / BOOKING CONVENTIONS" backHref="/instruments" backLabel="Back to instruments"><p className="workspace-subtitle">{instrument.canonicalName}</p><p>Tenant-owned instruments only. Submit a sourced convention for Operations approval; existing approved versions and booked trades remain immutable.</p></WorkspacePageHeader><ProductFacts terms={terms.data} configuration/>{terms.data.convention?.kind==='FUTURE'&&terms.data.convention.priceBasis!=='INDEX_POINTS'?<p className="configuration-impact">This contract is creation-only. Crypto futures trade booking, convention amendments and delivery processing are deferred.</p>:<ProductConventionForm kind={kind} currencies={currencies.data} tenantId={context.tenantId} instrumentId={instrumentId} currencyCode={instrument.baseCurrency} current={terms.data.convention}/>}</main></WorkspaceShell>;}catch{return <WorkspaceShell {...shell}><main className="mvp-page"><WorkspacePageHeader title="Booking conventions" eyebrow="INSTRUMENTS / BOOKING CONVENTIONS" backHref="/instruments" backLabel="Back to instruments"/><p role="alert" className="error-panel">Instrument conventions or currency catalogue unavailable. Try again when the service is available.</p></main></WorkspaceShell>;}
}
