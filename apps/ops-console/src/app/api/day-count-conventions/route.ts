import { NextResponse } from "next/server";

import { listDayCountConventions } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { bffErrorResponse } from "@/lib/bff-error";

export async function GET(request: Request) {
  try {
    const result = await listDayCountConventions(await getActiveTenantContext());
    return NextResponse.json(result);
  } catch (error) {
    return bffErrorResponse(error, "Day-count conventions could not be loaded", request, "DAY_COUNT_CATALOGUE_UNAVAILABLE");
  }
}
