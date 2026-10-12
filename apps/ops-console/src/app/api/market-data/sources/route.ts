import {NextRequest,NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
import {SessionRequiredError} from '@/lib/server/workspace-errors';
export const dynamic='force-dynamic';
function sourceError(error:unknown,message:string,request:NextRequest){
 if(error instanceof SessionRequiredError){
  const correlationId=crypto.randomUUID();
  return NextResponse.json({error:{code:'ACTIVE_TENANT_REQUIRED',message:'Select a tenant before viewing or changing source configuration.',retryable:false,correlationId}},
   {status:401,headers:{'X-Correlation-Id':correlationId}});
 }
 return bffErrorResponse(error,message,request);
}
export async function GET(request:NextRequest){
 try{
  const result=await(await pricingPolicyClient()).GET('/v1/market-data/sources');
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return sourceError(error,'Source configuration is unavailable.',request);}
}
export async function POST(request:NextRequest){
 const key=request.headers.get('Idempotency-Key');
 if(!key?.trim()||key.length>255)return NextResponse.json({error:{message:'A stable submission key is required.'}},{status:400});
 let body;
 try{body=await request.json();}catch{return NextResponse.json({error:{message:'Valid JSON is required.'}},{status:400});}
 try{
  const result=await(await pricingPolicyClient()).POST('/v1/market-data/source-priorities',{body,params:{header:{'Idempotency-Key':key}}});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return sourceError(error,'Save outcome is uncertain. Retry unchanged or reload configuration before editing.',request);}
}
