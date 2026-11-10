import {NextRequest,NextResponse} from 'next/server';
import {requireReferenceTenantContext} from '@/lib/reference-tenant-context';
import {getEquityCreationOptions} from '@/lib/reference-api-client';
import {bffErrorResponse} from '@/lib/bff-error';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest){
  const day=request.nextUrl.searchParams.get('effectiveDate')??'';
  if(!/^\d{4}-\d{2}-\d{2}$/.test(day))return NextResponse.json({error:{message:'Select a valid effective date.'}},{status:400});
  try{return NextResponse.json(await getEquityCreationOptions(await requireReferenceTenantContext(),day));}
  catch(error){return bffErrorResponse(error,'Creation choices could not be loaded.',request);}
}
