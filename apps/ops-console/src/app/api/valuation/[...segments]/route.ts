import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {referenceFetch} from '@/lib/reference-fetch';
import {bffErrorResponse} from '@/lib/bff-error';
import {forwardWorkloadHeaders} from '@/lib/server/workload-response';

export const dynamic='force-dynamic';
type Context={params:Promise<{segments:string[]}>};
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** An allowlisted tenant BFF, never an arbitrary upstream proxy. */
async function forward(request:NextRequest,context:Context,method:'GET'|'POST') {
 const {segments}=await context.params;
 const allowed=method==='GET'
  ? (segments.length===1&&['options','option-choices','attempts','reassessments','accrual-inputs','cash-options','cash-accounts','cash-balances','interest-options','balance-inputs','balance-history','balance-series','balance-trades','interest-review'].includes(segments[0]))||(segments.length===2&&segments[0]==='attempts'&&uuid.test(segments[1]))||(segments.length===3&&segments[0]==='batches'&&uuid.test(segments[1])&&['amendments','mark-overrides'].includes(segments[2]))
  : (segments.length===1&&['attempts','accrual-inputs','economic-flows','cash-accounts','cash-balances','cash-balance-preview','mark-overrides','balance-inputs','balance-history-refresh','interest-review'].includes(segments[0]))||(segments.length===3&&segments[0]==='batches'&&uuid.test(segments[1])&&['explanations','publish','self-publish','amendments'].includes(segments[2]))||(segments.length===3&&segments[0]==='amendments'&&uuid.test(segments[1])&&['approve','reject'].includes(segments[2]))||(segments.length===3&&segments[0]==='mark-overrides'&&uuid.test(segments[1])&&['approve','reject','withdraw'].includes(segments[2]))||(segments.length===3&&segments[0]==='economic-flows'&&uuid.test(segments[1])&&segments[2]==='cancel');
 const reassessment=method==='POST'&&segments.length===2&&segments[0]==='reassessments'&&segments[1]==='recalculate';
 const balanceBuild=method==='GET'&&segments.length===2&&segments[0]==='balance-builds'&&uuid.test(segments[1]);
 if(!allowed&&!reassessment&&!balanceBuild)return NextResponse.json({error:{message:'Valuation route not found.'}},{status:404});
 try {
  const tenant=await getActiveTenantContext();
  const headers=new Headers({'X-Tenant-Id':tenant.tenantId,'X-User-Account-Id':tenant.userAccountId,'Content-Type':'application/json'});
  const key=request.headers.get('Idempotency-Key');
  if(method==='POST'&&(segments.length===1||segments[2]==='amendments'||segments[0]==='economic-flows'||reassessment)) {
   if(!key?.trim()||key.length>255)return NextResponse.json({error:{message:'A stable request key is required.'}},{status:400});
   headers.set('Idempotency-Key',key);
  }
  const query=new URLSearchParams();
  if(method==='GET'&&segments[0]==='option-choices')for(const name of ['kind','q','limit','offset','selected_id','strategy_id','for_calculation']) {
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  if(method==='GET'&&segments[0]==='reassessments')for(const name of ['limit','offset','strategy_id']) {
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  if(method==='GET'&&segments[0]==='attempts'&&segments.length===1)for(const name of ['limit','offset','strategy_id','from_date','to_date','calculation_status','publication_status','results_only']) {
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  if(method==='GET'&&['accrual-inputs','balance-inputs','balance-history','interest-options'].includes(segments[0]))for(const name of ['strategyId','fromDate','toDate','limit','offset',...(segments[0]==='balance-history'?['instrumentId']:[])]){
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  if(method==='GET'&&segments[0]==='interest-review')for(const name of ['strategyId','valueDate','stage']){
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  if(method==='GET'&&['balance-series','balance-trades'].includes(segments[0]))for(const name of ['strategyId','instrumentId','fromDate','toDate']){
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  if(method==='GET'&&['cash-accounts','cash-balances'].includes(segments[0]))for(const name of ['strategyId','valueDate']){
   const value=request.nextUrl.searchParams.get(name);if(value!==null)query.set(name,value);
  }
  const response=await referenceFetch()(`${process.env.REFERENCE_API_URL??'http://localhost:8000'}/v1/valuation/${segments.join('/')}${query.size?'?'+query:''}`,{
   method,headers,cache:'no-store',...(method==='POST'?{body:JSON.stringify(await request.json())}:{})});
  const result=NextResponse.json(await response.json(),{status:response.status});
  const correlation=response.headers.get('X-Correlation-Id');if(correlation)result.headers.set('X-Correlation-Id',correlation);
  return forwardWorkloadHeaders(response,result);
 }catch(error){return bffErrorResponse(error,'Valuation service is unavailable. A timed-out calculation may still have completed; retry unchanged with the same key.',request);}
}
export function GET(request:NextRequest,context:Context){return forward(request,context,'GET');}
export function POST(request:NextRequest,context:Context){return forward(request,context,'POST');}
