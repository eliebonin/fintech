import { NextResponse } from "next/server";

import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { getWorkQueue } from "@/lib/work-queue";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export function GET(request: Request) {
  const context = resolveLocalTenantContext();
  return getWorkQueue(context)
    .then((payload) => NextResponse.json(payload))
    .catch((error: unknown) => {
      const localFallbackAllowed = process.env.APP_ENV !== "production" && process.env.ALLOW_SYNTHETIC_FALLBACK !== "false";
      if (!localFallbackAllowed) {
        return bffErrorResponse(error, "Reference data service is unavailable", request, "REFERENCE_API_UNAVAILABLE");
      }
      return NextResponse.json({
        counts: { MAPPING_REVIEW: 1, REFERENCE_DATA_REVIEW: 0, NAV_REVIEW: 0, MARKET_DATA_EXCEPTION: 0 },
        items: [
          { itemId: "mapping:fixture-pending", category: "MAPPING_REVIEW", title: "Verify PENDING-HSBC-XLON", detail: "CUSTODIAN_B_ASSET_PROD → HSBC XLON listing", status: "PENDING", referenceId: "fixture-pending" },
        ],
        meta: {
          tenantContext: context.tenantId,
          source: "synthetic-fixture-fallback",
          apiVersion: "fixture-v1",
          correlationId: request.headers.get("X-Correlation-Id") ?? crypto.randomUUID(),
          warning: "Reference API unavailable; synthetic queue is shown for local development only.",
        },
      });
    });
}
