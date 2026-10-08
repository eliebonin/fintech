import {NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {bffErrorResponse} from '@/lib/bff-error';
export async function GET(request:Request,{params}:{params:Promise<{policyId:string}>}) {
 try {const {policyId}=await params;const result=await (await pricingPolicyClient()).GET('/v1/market-data/valuation-policies/{policy_id}',{params:{path:{policy_id:policyId}}});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return bffErrorResponse(error,'Pricing-policy version is unavailable.',request);}
}
