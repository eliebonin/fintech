import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {referenceFetch} from '@/lib/reference-fetch';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
type Context={params:Promise<{segments:string[]}>};
async function forward(request:NextRequest,context:Context,method:'GET'|'POST'){
 const {segments}=await context.params;const path=segments.join('/');
 const fxPath=path.startsWith('fx-forward/')?path.slice('fx-forward/'.length):null;
 const couponPath=path.startsWith('coupons/')?path.slice('coupons/'.length):null;
 const couponAllowed=couponPath!==null&&(method==='GET'?['options','schedule','payments','history'].includes(couponPath):['schedules','payments','payments/correct','payments/reverse'].includes(couponPath));
 const fxAllowed=fxPath!==null&&(method==='GET'?['options','closures','closures/postings'].includes(fxPath):
  ['policy','closures/preview','closures/prepare','closures/book','closures/approve','closures/cancel'].includes(fxPath));
 const allowed=couponAllowed||fxAllowed||(method==='GET'?['options','bond-redemptions','bond-redemptions/postings'].includes(path):
  ['policy','bond-redemptions/preview','bond-redemptions/prepare','bond-redemptions/book','bond-redemptions/approve','bond-redemptions/cancel'].includes(path));
 if(!allowed)return NextResponse.json({error:{message:'Lifecycle route not found.'}},{status:404});
 try{
  const context=await getActiveTenantContext();const headers=new Headers({'X-Tenant-Id':context.tenantId,'X-User-Account-Id':context.userAccountId,'Content-Type':'application/json'});
  const key=request.headers.get('Idempotency-Key');if(method==='POST'&&(couponAllowed||['bond-redemptions/book','bond-redemptions/approve','bond-redemptions/cancel'].includes(path)||['closures/book','closures/approve','closures/cancel'].includes(fxPath??''))){
   if(!key?.trim()||key.length>255)return NextResponse.json({error:{message:'A stable booking request key is required.'}},{status:400});headers.set('Idempotency-Key',key);
  }
  const query=new URLSearchParams();if(method==='GET')for(const name of ['strategyId','limit','offset','instrumentId','scheduleId','paymentId','fromDate','toDate']){const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);}
  const response=await referenceFetch()(`${process.env.REFERENCE_API_URL??'http://localhost:8000'}/v1/lifecycle/${path}${query.size?'?'+query:''}`,{method,headers,cache:'no-store',...(method==='POST'?{body:JSON.stringify(await request.json())}:{})});
  return NextResponse.json(await response.json(),{status:response.status});
 }catch(error){return bffErrorResponse(error,'Lifecycle service unavailable. Retry an unchanged booking with the same request key.',request);}
}
export function GET(request:NextRequest,context:Context){return forward(request,context,'GET');}
export function POST(request:NextRequest,context:Context){return forward(request,context,'POST');}
