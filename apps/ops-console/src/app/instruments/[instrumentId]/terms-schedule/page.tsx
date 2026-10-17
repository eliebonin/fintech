import {notFound,redirect} from 'next/navigation';
import {resolveWorkspaceAccess} from '@/lib/server/workspace-access';
import {WorkspaceUnavailable} from '@/components/workspace-unavailable';
import {WorkspaceShell} from '@/components/workspace-shell';
import {InstrumentTermsSchedule} from '@/components/instrument-terms-schedule';
import {getInstrumentTermsSchedule,MvpApiError,describeMvpError} from '@/lib/mvp-api-client';

export const dynamic='force-dynamic';
export default async function TermsSchedulePage({params}:{params:Promise<{instrumentId:string}>}) {
  const {instrumentId}=await params;
  const access=await resolveWorkspaceAccess();
  if(access.kind==='session-required')redirect('/select-tenant');
  if(access.kind!=='ready')return <WorkspaceUnavailable forbidden={access.kind==='forbidden'}/>;
  const {context,workspace}=access;
  let data;
  try {data=(await getInstrumentTermsSchedule(context,instrumentId)).data;}
  catch(error) {
    if(error instanceof MvpApiError&&error.status===404)notFound();
    return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel="API UNAVAILABLE"><p role="alert">{describeMvpError(error,'Terms and schedule')}</p></WorkspaceShell>;
  }
  return <WorkspaceShell tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes} permissionCodes={workspace.permissionCodes} userName={workspace.userName} actorId={workspace.actorId} sourceLabel="LIVE API"><InstrumentTermsSchedule data={data}/></WorkspaceShell>;
}
