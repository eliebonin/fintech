import { NextResponse } from "next/server";

import { listDayCountConventions } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export async function GET(request: Request) {
  try {
    const result = await listDayCountConventions(resolveLocalTenantContext());
    return NextResponse.json(result);
  } catch (error) {
    return bffErrorResponse(error, "Day-count conventions could not be loaded", request, "DAY_COUNT_CATALOGUE_UNAVAILABLE");
  }
}
