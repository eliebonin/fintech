import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {referenceFetch} from '@/lib/reference-fetch';
import {bffErrorResponse} from '@/lib/bff-error';

export const dynamic='force-dynamic';
type Context={params:Promise<{segments:string[]}>};
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** An allowlisted tenant BFF, never an arbitrary upstream proxy. */
async function forward(request:NextRequest,context:Context,method:'GET'|'POST') {
 const {segments}=await context.params;
 const allowed=method==='GET'
  ? (segments.length===1&&['options','attempts'].includes(segments[0]))||(segments.length===2&&segments[0]==='attempts'&&uuid.test(segments[1]))
  : (segments.length===1&&segments[0]==='attempts')||(segments.length===3&&segments[0]==='batches'&&uuid.test(segments[1])&&['explanations','publish'].includes(segments[2]));
 if(!allowed)return NextResponse.json({error:{message:'Valuation route not found.'}},{status:404});
 try {
  const tenant=await getActiveTenantContext();
  const headers=new Headers({'X-Tenant-Id':tenant.tenantId,'X-User-Account-Id':tenant.userAccountId,'Content-Type':'application/json'});
  const key=request.headers.get('Idempotency-Key');
  if(method==='POST'&&segments[0]==='attempts') {
   if(!key?.trim()||key.length>255)return NextResponse.json({error:{message:'A stable request key is required.'}},{status:400});
   headers.set('Idempotency-Key',key);
  }
  const query=new URLSearchParams();
  if(method==='GET'&&segments[0]==='attempts'&&segments.length===1)for(const name of ['limit','offset']) {
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  const response=await referenceFetch()(`${process.env.REFERENCE_API_URL??'http://localhost:8000'}/v1/valuation/${segments.join('/')}${query.size?'?'+query:''}`,{
   method,headers,cache:'no-store',...(method==='POST'?{body:JSON.stringify(await request.json())}:{})});
  const result=NextResponse.json(await response.json(),{status:response.status});
  const correlation=response.headers.get('X-Correlation-Id');if(correlation)result.headers.set('X-Correlation-Id',correlation);
  return result;
 }catch(error){return bffErrorResponse(error,'Valuation service is unavailable. A timed-out calculation may still have completed; retry unchanged with the same key.',request);}
}
export function GET(request:NextRequest,context:Context){return forward(request,context,'GET');}
export function POST(request:NextRequest,context:Context){return forward(request,context,'POST');}
