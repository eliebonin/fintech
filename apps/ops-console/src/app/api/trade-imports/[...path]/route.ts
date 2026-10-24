import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {readBookingWrite} from '@/lib/booking-write-guard';
import {referenceFetch} from '@/lib/reference-fetch';
import {bffErrorResponse} from '@/lib/bff-error';

export const dynamic='force-dynamic';
export async function GET(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){return proxy(request,ctx);}
export async function POST(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){return proxy(request,ctx);}
async function proxy(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){
 const path=(await ctx.params).path.join('/');
 const uuid='[0-9a-fA-F-]{36}';
 const allowed=request.method==='GET'
  ?new RegExp(`^(history|options|template|${uuid}(?:/(?:errors|artifact))?)$`).test(path)
  :new RegExp(`^(create|${uuid}/(?:validate|confirm))$`).test(path);
 if(!allowed)return NextResponse.json({error:{message:'Unknown import action.'}},{status:404});
 if(Number(request.headers.get('Content-Length')??0)>1048576)return NextResponse.json({error:{message:'Upload request exceeds 1 MiB.'}},{status:413});
 try{
  const envelope=request.method==='POST'?await readBookingWrite(request):null;
  if(envelope?.response)return envelope.response;
  const context=envelope?.context??await getActiveTenantContext();
  const suffix=path==='history'||path==='create'?'':`/${path}`;
  const response=await referenceFetch()(new URL(`/v1/trades/imports${suffix}${request.nextUrl.search}`,process.env.REFERENCE_API_URL??'http://127.0.0.1:8000'),{
   method:request.method,cache:'no-store',headers:{'Content-Type':'application/json','X-Tenant-Id':context.tenantId,'X-User-Account-Id':context.userAccountId,
    ...(envelope?.key?{'Idempotency-Key':envelope.key}:{})},...(envelope?{body:JSON.stringify(envelope.payload)}:{}),
  });
  const headers=new Headers({'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'});
  for(const name of ['Content-Type','Content-Disposition','X-Request-Id']){const value=response.headers.get(name);if(value)headers.set(name,value);}
  return new NextResponse(response.body,{status:response.status,headers});
 }catch(error){return bffErrorResponse(error,'Import service is unavailable. Check import history before retrying a booking.',request);}
}
