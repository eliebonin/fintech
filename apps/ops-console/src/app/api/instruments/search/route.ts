import { NextRequest, NextResponse } from "next/server";

import { searchInstruments } from "@/lib/instrument-data";
import { searchReferenceInstruments } from "@/lib/reference-api-client";
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
  return searchReferenceInstruments(query, { ...context, instrumentType, assetClass, status, limit, offset })
    .then((payload) => NextResponse.json(payload))
    .catch((error: unknown) => {
      const localFallbackAllowed = process.env.APP_ENV !== "production" && process.env.ALLOW_SYNTHETIC_FALLBACK !== "false";
      if (!localFallbackAllowed) {
        return bffErrorResponse(error, "Reference data service is unavailable", request, "REFERENCE_API_UNAVAILABLE");
      }
      return NextResponse.json({
        data: searchInstruments(query),
        meta: {
          tenantContext: context.tenantId,
          source: "synthetic-fixture-fallback",
          apiVersion: "fixture-v1",
          correlationId: request.headers.get("X-Correlation-Id") ?? crypto.randomUUID(),
          warning: "Reference API unavailable; synthetic fixtures are shown for local development only.",
        },
      });
    });
}
