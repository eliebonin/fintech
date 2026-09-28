import { NextRequest, NextResponse } from "next/server";

import { listOrganisations } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.get("q") ?? "";
    return NextResponse.json(await listOrganisations(resolveLocalTenantContext(), query));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
