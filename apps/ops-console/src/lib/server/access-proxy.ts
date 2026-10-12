import 'server-only';
import {cookies} from 'next/headers';
import {getActiveTenantContext} from '../tenant-session';
import {referenceFetch} from '../reference-fetch';

export function requireLocalMode() {
  if (process.env.NODE_ENV==='production' || !['local','test','development'].includes(process.env.APP_ENV??'local'))
    throw new Error('Local context switching is disabled outside development');
}

export function sameOrigin(request:Request) {
  const origin=request.headers.get('origin');
  if (!origin || origin!==new URL(request.url).origin) throw new Error('A same-origin request is required');
}

export async function accessProxy(path:string,init:RequestInit={},mode:'tenant'|'platform'|'operator'='tenant') {
  const headers=new Headers(init.headers);
  headers.set('Accept','application/json');
  headers.set('Content-Type','application/json');
  const token=(await cookies()).get('local_access_session')?.value;
  if (mode==='operator') {
    requireLocalMode();
    headers.set('X-User-Account-Id',process.env.LOCAL_PLATFORM_OPERATOR_ID??'00000000-0000-7000-8000-000000000304');
  } else if (mode==='platform') {
    requireLocalMode();
    if (!token) throw new Error('Select platform context first');
    const current=await referenceFetch()(new URL('/v1/local-session',process.env.REFERENCE_API_URL??'http://localhost:8000'),{
      headers:{'X-Local-Access-Token':token},cache:'no-store'});
    if (!current.ok) return current;
    const selected=await current.json() as {tenantId:string|null;userId:string};
    if (selected.tenantId) return Response.json({error:{message:'Return to platform mode before administering tenants.'}},{status:403});
    headers.set('X-User-Account-Id',selected.userId);
  } else {
    const context=await getActiveTenantContext();
    headers.set('X-Tenant-Id',context.tenantId);headers.set('X-User-Account-Id',context.userAccountId);
  }
  if (token) headers.set('X-Local-Access-Token',token);
  return referenceFetch()(new URL(path,process.env.REFERENCE_API_URL??'http://localhost:8000'),{...init,headers,cache:'no-store'});
}
