import { NextRequest, NextResponse } from "next/server";
import { searchTradeTraders } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { bffErrorResponse } from "@/lib/bff-error";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") ?? "";
  if (query.length > 250) return NextResponse.json({error:{message:"Search must be at most 250 characters."}},{status:400});
  try { return NextResponse.json(await searchTradeTraders(await getActiveTenantContext(),query)); }
  catch (error) { return bffErrorResponse(error,"Trader lookup is unavailable.",request); }
}
