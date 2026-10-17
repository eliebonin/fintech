import {NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
function forwardResult(result:{data?:unknown;error?:unknown;response:Response}) {
  const headers=new Headers({'Cache-Control':'no-store'});
  for(const name of ['X-Request-Id','X-Correlation-Id']) {
    const value=result.response.headers.get(name);if(value)headers.set(name,value);
  }
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status,headers});
}
export async function GET(request:Request) {
  try {
    const result=await(await pricingPolicyClient()).GET('/v1/structured-product-proposals/calendar-options');
    return forwardResult(result);
  } catch(error) {return bffErrorResponse(error,'Published contractual calendars could not be loaded.',request);}
}
export async function POST(request:Request) {
  let body;
  try {body=await request.json();}
  catch {return NextResponse.json({error:{code:'INVALID_JSON',message:'Enter a valid payment-date request.'}},{status:400});}
  try {
    const result=await(await pricingPolicyClient()).POST('/v1/structured-product-proposals/payment-dates',{body});
    return forwardResult(result);
  } catch(error) {return bffErrorResponse(error,'Contractual payment dates could not be assessed.',request);}
}
