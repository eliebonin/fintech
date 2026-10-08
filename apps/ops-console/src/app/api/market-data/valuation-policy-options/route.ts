import {NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export async function GET(request:Request) {
 try {const result=await (await pricingPolicyClient()).GET('/v1/market-data/valuation-policy-options');
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return bffErrorResponse(error,'Pricing-policy options are unavailable.',request);}
}
