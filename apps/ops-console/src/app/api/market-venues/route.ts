import { NextResponse } from "next/server";

import { listMarketVenues } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = resolveLocalTenantContext();
  try {
    return NextResponse.json(await listMarketVenues(context));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
