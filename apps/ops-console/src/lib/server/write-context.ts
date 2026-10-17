import 'server-only';
import {NextResponse} from 'next/server';
import {getActiveTenantContext} from '../tenant-session';
import type {TenantContext} from '../tenant-types';
import {SessionRequiredError,WorkspaceApiError} from './workspace-errors';

type WriteContextResult={context:TenantContext;response?:never}|{response:NextResponse;context?:never};

/** Expected identity binds form intent; only the resolved session supplies authority. */
export async function readWriteContext(request:Request):Promise<WriteContextResult>{
 const fail=(status:number,code:string,message:string):WriteContextResult=>({response:NextResponse.json(
  {error:{code,message}},{status,headers:{'Cache-Control':'no-store'}})});
 const expectedTenant=request.headers.get('X-Expected-Tenant-Id')?.trim();
 const expectedUser=request.headers.get('X-Expected-User-Id')?.trim();
 if(!expectedTenant||!expectedUser)return fail(400,'WRITE_CONTEXT_REQUIRED','Reopen this form to confirm its tenant and user before saving.');
 let context:TenantContext;
 try{context=await getActiveTenantContext();}
 catch(error){
  if(error instanceof SessionRequiredError||error instanceof WorkspaceApiError&&error.status===401)
   return fail(401,'ACTIVE_TENANT_REQUIRED','Select a tenant and user, then reopen this form.');
  if(error instanceof WorkspaceApiError&&error.status===403)
   return fail(403,'ACCESS_FORBIDDEN','Your selected context is no longer available. Select a context and reopen this form.');
  return fail(503,'CONTEXT_UNAVAILABLE','The current context could not be verified. Nothing was submitted. Try again later.');
 }
 if(expectedTenant!==context.tenantId||expectedUser!==context.userAccountId)
  return fail(409,'TENANT_CONTEXT_CHANGED','Tenant or user context changed. Reload this page before saving; nothing was submitted.');
 return {context};
}
