import { NextRequest, NextResponse } from "next/server";
import { getTradeBookingContext } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { bffErrorResponse } from "@/lib/bff-error";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  try { return NextResponse.json(await getTradeBookingContext(await getActiveTenantContext())); }
  catch (error) { return bffErrorResponse(error,"Trade booking context is unavailable.",request); }
}
