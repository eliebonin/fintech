import { NextRequest, NextResponse } from "next/server";
import { getTradeBookingContext } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { bffErrorResponse } from "@/lib/bff-error";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  try {
    const context=await getActiveTenantContext();
    const expected=request.headers.get('X-Expected-Tenant-Id');
    if(expected&&expected!==context.tenantId)return NextResponse.json({error:{message:'Tenant context changed. Reload before booking.'}},{status:409});
    return NextResponse.json(await getTradeBookingContext(context,request.nextUrl.searchParams.get("strategyId")??undefined,request.nextUrl.searchParams.get("corrects")??undefined));
  }
  catch (error) { return bffErrorResponse(error,"Trade booking context is unavailable.",request); }
}
