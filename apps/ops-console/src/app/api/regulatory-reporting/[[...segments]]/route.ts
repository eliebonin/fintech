import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {referenceFetch} from '@/lib/reference-fetch';
import {bffErrorResponse} from '@/lib/bff-error';
import {forwardWorkloadHeaders} from '@/lib/server/workload-response';
export const dynamic='force-dynamic';
type Context={params:Promise<{segments?:string[]}>};
const uuid='[0-9a-fA-F]{8}-[0-9a-fA-F-]{27}';
async function forward(request:NextRequest,context:Context,method:'GET'|'POST'){
 const path=((await context.params).segments??[]).join('/');
 const allowed=method==='GET'?['options','profiles','candidates','export-preview','exports'].includes(path)||new RegExp(`^(candidates|exports)/${uuid}$`).test(path):
  ['profiles','prepare','exports'].includes(path)||new RegExp(`^profiles/${uuid}$|^candidates/${uuid}/review$`).test(path);
 if(!allowed)return NextResponse.json({error:{message:'Reporting route not found.'}},{status:404});
 try{
  const trusted=await getActiveTenantContext();
  const headers=new Headers({'X-Tenant-Id':trusted.tenantId,'X-User-Account-Id':trusted.userAccountId,'Content-Type':'application/json'});
  if(method==='POST'&&path==='exports'){
   const key=request.headers.get('Idempotency-Key');
   if(!key?.trim()||key.length>200)return NextResponse.json({error:{message:'A stable export request key is required.'}},{status:400});
   headers.set('Idempotency-Key',key);
  }
  const query=new URLSearchParams();
  for(const name of ['profileId','strategyId','fromDate','toDate','status','limit','offset','forAction']){
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  const response=await referenceFetch()(`${process.env.REFERENCE_API_URL??'http://localhost:8000'}/v1/regulatory-reporting/${path}${query.size?'?'+query:''}`,
   {method,headers,cache:'no-store',...(method==='POST'?{body:JSON.stringify(await request.json())}:{})});
  return forwardWorkloadHeaders(response,NextResponse.json(await response.json(),{status:response.status,headers:{'Cache-Control':'no-store'}}));
 }catch(error){return bffErrorResponse(error,'Regulatory Reporting could not complete this request. Check export history before retrying a changed export.',request);}
}
export function GET(request:NextRequest,context:Context){return forward(request,context,'GET');}
export function POST(request:NextRequest,context:Context){return forward(request,context,'POST');}
