import { NextResponse } from "next/server";

import { listCurrencies } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const groups = new URL(request.url).searchParams.get("groups");
    const selectedGroups = groups ? groups.split(",").map((group) => group.trim().toUpperCase()).filter(Boolean) as ("REGULAR" | "CRYPTO")[] : undefined;
    return NextResponse.json(await listCurrencies(resolveLocalTenantContext(), selectedGroups));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
