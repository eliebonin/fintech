import { NextRequest,NextResponse } from 'next/server';
import { bffErrorResponse } from '@/lib/bff-error';
import { bookOptionTrade } from '@/lib/reference-api-client';
import { getActiveTenantContext } from '@/lib/tenant-session';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest) {
  const key=request.headers.get('Idempotency-Key')?.trim(),expected=request.headers.get('X-Expected-Tenant-Id');
  if(!key)return NextResponse.json({error:{code:'IDEMPOTENCY_KEY_REQUIRED',message:'Idempotency-Key is required.'}},{status:400});
  if(!expected)return NextResponse.json({error:{code:'EXPECTED_TENANT_REQUIRED',message:'Reopen the ticket to confirm its tenant.'}},{status:400});
  let payload;try{payload=await request.json();}catch{return NextResponse.json({error:{code:'INVALID_JSON',message:'Request body must be valid JSON.'}},{status:400});}
  let context;try{context=await getActiveTenantContext();}catch{return NextResponse.json({error:{code:'ACTIVE_TENANT_REQUIRED'}},{status:401});}
  if(expected!==context.tenantId)return NextResponse.json({error:{code:'TENANT_CONTEXT_CHANGED',message:'The active tenant changed. Restart the ticket.'}},{status:409});
  try{return NextResponse.json(await bookOptionTrade(payload,context,key),{status:201});}
  catch(error){return bffErrorResponse(error,'Option booking is unavailable',request,'TRADE_BOOKING_API_UNAVAILABLE');}
}
