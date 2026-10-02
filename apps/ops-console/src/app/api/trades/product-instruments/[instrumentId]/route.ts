import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from '@/lib/tenant-session';
import {getProductInstrument} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,{params}:{params:Promise<{instrumentId:string}>}) {
  try{return NextResponse.json(await getProductInstrument(await getActiveTenantContext(),(await params).instrumentId,request.nextUrl.searchParams));}
  catch(error){return bffErrorResponse(error,'Product terms unavailable',request,'PRODUCT_CONTEXT_UNAVAILABLE');}
}
