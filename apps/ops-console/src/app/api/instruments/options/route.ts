import { NextRequest,NextResponse } from 'next/server';
import { bffErrorResponse } from '@/lib/bff-error';
import { submitOptionProposal } from '@/lib/reference-api-client';
import { getActiveTenantContext } from '@/lib/tenant-session';
export const dynamic='force-dynamic';
export async function POST(request:NextRequest) {
  let payload;try{payload=await request.json();}catch{return NextResponse.json({error:{message:'Invalid JSON.'}},{status:400});}
  try{return NextResponse.json(await submitOptionProposal(payload,await getActiveTenantContext()),{status:201});}
  catch(error){return bffErrorResponse(error,'Option proposal is unavailable',request,'OPTION_PROPOSAL_UNAVAILABLE');}
}
