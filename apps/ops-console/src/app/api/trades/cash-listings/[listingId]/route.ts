import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {getCashBookingListing} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,{params}:{params:Promise<{listingId:string}>}) {
  try{return NextResponse.json(await getCashBookingListing(await getActiveTenantContext(),(await params).listingId,request.nextUrl.searchParams.get('asOfDate')??undefined));}
  catch(error){return bffErrorResponse(error,'Cash listing readiness unavailable',request,'CASH_READINESS_UNAVAILABLE');}
}
