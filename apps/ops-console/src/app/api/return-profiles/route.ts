import { NextResponse } from "next/server";

import { listReturnProfiles } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    return NextResponse.json(await listReturnProfiles(resolveLocalTenantContext()));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
