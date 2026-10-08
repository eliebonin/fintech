import { NextRequest,NextResponse } from 'next/server';
import { bffErrorResponse } from '@/lib/bff-error';
import { searchOptionBookingListings } from '@/lib/reference-api-client';
import { getActiveTenantContext } from '@/lib/tenant-session';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest) {
  const offset=Number(request.nextUrl.searchParams.get('offset')??0);
  if(!Number.isSafeInteger(offset)||offset<0)return NextResponse.json({error:{code:'INVALID_OFFSET',message:'Offset must be a non-negative integer.'}},{status:400});
  try{return NextResponse.json(await searchOptionBookingListings(await getActiveTenantContext(),request.nextUrl.searchParams.get('q')??'',offset,request.nextUrl.searchParams.get('asOfDate')??undefined));}
  catch(error){return bffErrorResponse(error,'Option search is unavailable',request,'OPTION_SEARCH_UNAVAILABLE');}
}
