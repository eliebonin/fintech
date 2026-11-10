import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {referenceFetch} from '@/lib/reference-fetch';
import {ReferenceApiError} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
const uuid='[0-9a-fA-F-]{36}';
function allowed(path:string,method:string){
 const read=[/^register$/,/^default$/,/^field-library$/, /^assignment-targets$/,new RegExp(`^versions/${uuid}$`),new RegExp(`^${uuid}/(versions|usage|history)$`),new RegExp(`^strategies/${uuid}$`)];
 const write=[/^assignments(\/preview)?$/,/^register$/,/^default$/,new RegExp(`^${uuid}/(versions|retire)$`),new RegExp(`^strategies/${uuid}(/preview)?$`)];
 return (method==='GET'?read:write).some(pattern=>pattern.test(path));
}
async function proxy(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){
 const path=(await ctx.params).path.join('/');
 if(!allowed(path,request.method))return NextResponse.json({error:{message:'Unknown trade-profile action.'}},{status:404});
 try{
  const context=await getActiveTenantContext();
  if(request.headers.get('X-Expected-Tenant-Id')!==context.tenantId)return NextResponse.json({error:{message:'Tenant context changed. Reload this page.'}},{status:409});
  const suffix=path==='register'?'':`/${path}`;
  const response=await referenceFetch()(new URL(`/v1/trade-profiles${suffix}${request.nextUrl.search}`,process.env.REFERENCE_API_URL??'http://localhost:8000'),{
   method:request.method,cache:'no-store',headers:{'Content-Type':'application/json','X-Tenant-Id':context.tenantId,'X-User-Account-Id':context.userAccountId},
   ...(request.method==='POST'?{body:JSON.stringify(await request.json())}:{}),
  });
  const body=await response.json();
  if(!response.ok)throw new ReferenceApiError(response.status,body.detail??'Profile action failed.',body.code??'profile.failed',response.headers.get('X-Request-Id')??undefined);
  return NextResponse.json(body,{status:response.status,headers:{'Cache-Control':'private, no-store'}});
 }catch(error){return bffErrorResponse(error,'Trade profiles are unavailable.',request);}
}
export const GET=proxy;
export const POST=proxy;
