import { NextRequest,NextResponse } from 'next/server';
import { bffErrorResponse } from '@/lib/bff-error';
import { getOptionBookingListing } from '@/lib/reference-api-client';
import { getActiveTenantContext } from '@/lib/tenant-session';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,{params}:{params:Promise<{listingId:string}>}) {
  try{return NextResponse.json(await getOptionBookingListing(await getActiveTenantContext(),(await params).listingId,request.nextUrl.searchParams.get('asOfDate')??undefined));}
  catch(error){return bffErrorResponse(error,'Option listing is unavailable',request,'OPTION_SEARCH_UNAVAILABLE');}
}
