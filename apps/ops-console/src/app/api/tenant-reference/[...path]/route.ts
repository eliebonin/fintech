import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {referenceFetch} from '@/lib/reference-fetch';
import {ReferenceApiError} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){
 const parts=(await ctx.params).path;
 if(!/^(sources|options|sources\/(catalogue:[0-9a-fA-F-]{36}|standard:(COUNTERPARTY|EXECUTING_BROKER|TRADER))(\/(entries|usage|history))?)$/.test(parts.join('/')))return NextResponse.json({error:{message:'Unknown reference-data query.'}},{status:404});
 try{
  const context=await getActiveTenantContext();
  if(request.headers.get('X-Expected-Tenant-Id')!==context.tenantId)return NextResponse.json({error:{message:'Tenant context changed. Reload this page.'}},{status:409});
  const response=await referenceFetch()(new URL(`/v1/tenant-reference/${parts.map(encodeURIComponent).join('/')}${request.nextUrl.search}`,process.env.REFERENCE_API_URL??'http://localhost:8000'),{cache:'no-store',headers:{'X-Tenant-Id':context.tenantId,'X-User-Account-Id':context.userAccountId}});
  const body=await response.json();if(!response.ok)throw new ReferenceApiError(response.status,body.detail??'Reference data unavailable.',body.code??'reference.failed',response.headers.get('X-Request-Id')??undefined);
  return NextResponse.json(body,{headers:{'Cache-Control':'private, no-store'}});
 }catch(error){return bffErrorResponse(error,'Reference data unavailable.',request);}
}
