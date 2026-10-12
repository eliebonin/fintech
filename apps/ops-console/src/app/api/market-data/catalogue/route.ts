import {NextRequest,NextResponse} from 'next/server';
import {getMarketDataCatalogue} from '@/lib/mvp-api-client';
import {requireReferenceTenantContext} from '@/lib/reference-tenant-context';
import {bffErrorResponse} from '@/lib/bff-error';
export async function GET(request:NextRequest){
 try{const p=request.nextUrl.searchParams;return NextResponse.json(await getMarketDataCatalogue(await requireReferenceTenantContext(),{q:p.get('q')??'',asOf:p.get('asOf')??undefined,limit:Number(p.get('limit')??25),offset:Number(p.get('offset')??0)}));}
 catch(e){return bffErrorResponse(e,'Market data catalogue is unavailable.',request);}
}
