import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from './tenant-session';
import {bookProductTrade,submitProductProposal} from './reference-api-client';
import {bffErrorResponse} from './bff-error';

export async function productWrite(request:NextRequest,kind:'structured-products'|'futures'|'future-families'|'bonds'|'swaps',proposal=false) {
  if(kind==='future-families'&&!proposal)return NextResponse.json({error:{message:'Families are not tradable.'}},{status:400});
  const key=request.headers.get('Idempotency-Key')?.trim(),expected=request.headers.get('X-Expected-Tenant-Id');
  if(!proposal&&!key)return NextResponse.json({error:{code:'IDEMPOTENCY_KEY_REQUIRED',message:'Idempotency-Key is required.'}},{status:400});
  if(!expected)return NextResponse.json({error:{code:'EXPECTED_TENANT_REQUIRED',message:'Reopen this page to confirm the tenant.'}},{status:400});
  let context;try{context=await getActiveTenantContext();}catch{return NextResponse.json({error:{code:'ACTIVE_TENANT_REQUIRED'}},{status:401});}
  if(expected!==context.tenantId)return NextResponse.json({error:{code:'TENANT_CONTEXT_CHANGED',message:'The active tenant changed. Restart.'}},{status:409});
  let payload;try{payload=await request.json();}catch{return NextResponse.json({error:{code:'INVALID_JSON',message:'Valid JSON is required.'}},{status:400});}
  try{return NextResponse.json(proposal?await submitProductProposal(kind==='future-families'?'future-families':kind==='futures'?'futures':'booking-conventions',payload,context):await bookProductTrade(kind==='swaps'?'swaps':kind==='bonds'?'bonds':kind==='futures'?'futures':'structured-products',payload,context,key!),{status:201});}
  catch(error){return bffErrorResponse(error,'Product write unavailable',request,'PRODUCT_WRITE_UNAVAILABLE');}
}
