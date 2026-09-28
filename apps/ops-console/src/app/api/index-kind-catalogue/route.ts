import { NextResponse } from "next/server";

import { listIndexKinds } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    return NextResponse.json(await listIndexKinds(resolveLocalTenantContext()));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
