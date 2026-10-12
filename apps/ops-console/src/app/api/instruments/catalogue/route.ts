import { NextRequest, NextResponse } from "next/server";

import { loadCatalogue } from "@/features/instruments/catalogue-data";
import { bffErrorResponse } from "@/lib/bff-error";
import { getActiveTenantContext } from "@/lib/tenant-session";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") ?? "";
  const instrumentType = request.nextUrl.searchParams.get("instrument_type") ?? undefined;
  const assetClass = request.nextUrl.searchParams.get("asset_class") ?? undefined;
  const status = request.nextUrl.searchParams.get("status") ?? undefined;
  const requestedLimit = Number(request.nextUrl.searchParams.get("limit") ?? "25");
  const requestedOffset = Number(request.nextUrl.searchParams.get("offset") ?? "0");
  const limit = Number.isInteger(requestedLimit) && requestedLimit >= 1 && requestedLimit <= 100 ? requestedLimit : 25;
  const offset = Number.isInteger(requestedOffset) && requestedOffset >= 0 ? requestedOffset : 0;
  let context;
  try {
    context = await getActiveTenantContext();
  } catch {
    return NextResponse.json({ error: { code: "ACTIVE_TENANT_REQUIRED" } }, { status: 401 });
  }
  return loadCatalogue(query, { ...context, instrumentType, assetClass, status, limit, offset, signal: request.signal })
    .then((payload) => NextResponse.json(payload))
    .catch((error: unknown) => bffErrorResponse(error, "Reference data service is unavailable", request, "REFERENCE_API_UNAVAILABLE"));
}
