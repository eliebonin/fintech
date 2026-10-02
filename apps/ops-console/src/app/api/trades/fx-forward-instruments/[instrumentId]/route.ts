import { NextRequest, NextResponse } from "next/server";
import { bffErrorResponse } from "@/lib/bff-error";
import { getFxForwardBookingInstrument } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
export const dynamic="force-dynamic";
export async function GET(request:NextRequest,{params}:{params:Promise<{instrumentId:string}>}) {
  try{return NextResponse.json(await getFxForwardBookingInstrument(await getActiveTenantContext(),(await params).instrumentId));}
  catch(error){return bffErrorResponse(error,"FX-forward terms are unavailable",request,"FX_FORWARD_TERMS_UNAVAILABLE");}
}
