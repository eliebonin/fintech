import {NextRequest,NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest){
 try{const result=await(await pricingPolicyClient()).POST('/v1/market-data/policy-compatibility',{body:await request.json()});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return bffErrorResponse(error,'Compatibility could not be checked; no policy was saved.',request);}
}
