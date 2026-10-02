import type {NextRequest} from 'next/server';
import {NextResponse} from 'next/server';
import type {components} from 'api-contracts';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {submitSwapProposal} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest) {
  const expected=request.headers.get('X-Expected-Tenant-Id');
  if(!expected)return NextResponse.json({error:{code:'EXPECTED_TENANT_REQUIRED',message:'Reopen this page to confirm the tenant.'}},{status:400});
  let context;try{context=await getActiveTenantContext();}catch{return NextResponse.json({error:{code:'ACTIVE_TENANT_REQUIRED',message:'Select an active tenant.'}},{status:401});}
  if(expected!==context.tenantId)return NextResponse.json({error:{code:'TENANT_CONTEXT_CHANGED',message:'The active tenant changed. Reopen creation.'}},{status:409});
  let payload:components['schemas']['SwapProposalRequest'];
  try{payload=await request.json();}catch{return NextResponse.json({error:{code:'INVALID_JSON',message:'Valid JSON is required.'}},{status:400});}
  try{return NextResponse.json(await submitSwapProposal(context,payload),{status:201});}
  catch(error){return bffErrorResponse(error,'Swap proposal service unavailable',request);}
}
