import {NextResponse} from 'next/server';
import {pricingPolicyClient} from '@/lib/pricing-policy-api';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {bffErrorResponse} from '@/lib/bff-error';
export async function POST(request:Request) {
 try {const expected=request.headers.get('X-Expected-Tenant-Id');if(expected&&(await getActiveTenantContext()).tenantId!==expected)return NextResponse.json({error:{code:'TENANT_CONTEXT_CHANGED'}},{status:409});const body=await request.json();const result=await (await pricingPolicyClient()).POST('/v1/market-data/resolution-preview',{body});
  return NextResponse.json(result.data??{error:result.error},{status:result.response.status});
 }catch(error){return bffErrorResponse(error,'Input preview is unavailable; no snapshot was saved.',request);}
}
