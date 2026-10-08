import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {searchCashBookingListings} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest) {
  try{return NextResponse.json(await searchCashBookingListings(await getActiveTenantContext(),request.nextUrl.searchParams));}
  catch(error){return bffErrorResponse(error,'Cash listing readiness unavailable',request,'CASH_READINESS_UNAVAILABLE');}
}
