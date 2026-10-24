import type {NextRequest} from 'next/server';
import {NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {submitAmcProposal} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export async function POST(request:NextRequest){
  const expected=request.headers.get('X-Expected-Tenant-Id');
  if(!expected)return NextResponse.json({error:{message:'Reopen AMC creation to confirm the tenant.'}},{status:400});
  let context;try{context=await getActiveTenantContext();}catch{return NextResponse.json({error:{message:'Select a tenant.'}},{status:401});}
  if(context.tenantId!==expected)return NextResponse.json({error:{message:'Tenant changed. Reopen AMC creation.'}},{status:409});
  let payload;try{payload=await request.json();}catch{return NextResponse.json({error:{message:'Valid JSON is required.'}},{status:400});}
  try{return NextResponse.json(await submitAmcProposal(context,payload),{status:201});}
  catch(error){return bffErrorResponse(error,'AMC proposal unavailable',request);}
}
