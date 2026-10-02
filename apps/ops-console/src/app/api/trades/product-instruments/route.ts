import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {searchProductInstruments} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest) {
  try{return NextResponse.json(await searchProductInstruments(await getActiveTenantContext(),request.nextUrl.searchParams));}
  catch(error){return bffErrorResponse(error,'Product search unavailable',request,'PRODUCT_SEARCH_UNAVAILABLE');}
}
