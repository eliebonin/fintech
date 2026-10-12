import {NextRequest,NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest){
 try{const result=await(await pricingPolicyClient()).GET('/v1/market-data/policy-data-options');
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return bffErrorResponse(error,'Source compatibility metadata is unavailable.',request);}
}
