import {NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export async function POST(request:Request) {
 try {const body=await request.json();const result=await (await pricingPolicyClient()).POST('/v1/market-data/resolution-preview',{body});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return bffErrorResponse(error,'Input preview is unavailable; no snapshot was saved.',request);}
}
