import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {searchFutureFamilies} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
import {productWrite} from '@/lib/product-booking-bff';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest) {
  try{return NextResponse.json(await searchFutureFamilies(await getActiveTenantContext(),request.nextUrl.searchParams));}
  catch(error){return bffErrorResponse(error,'Family search unavailable',request,'FAMILY_SEARCH_UNAVAILABLE');}
}
export async function POST(request:NextRequest){return productWrite(request,'future-families',true);}
