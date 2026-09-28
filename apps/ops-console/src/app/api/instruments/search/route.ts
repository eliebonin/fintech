import { NextRequest, NextResponse } from "next/server";

import { searchInstruments } from "@/lib/instrument-data";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { searchReferenceInstruments } from "@/lib/reference-api-client";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") ?? "";
  const instrumentType = request.nextUrl.searchParams.get("instrument_type") ?? undefined;
  const assetClass = request.nextUrl.searchParams.get("asset_class") ?? undefined;
  const context = resolveLocalTenantContext();
  return searchReferenceInstruments(query, { ...context, instrumentType, assetClass })
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
