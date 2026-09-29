import { createReferenceApiClient } from "api-contracts";
import { NextRequest, NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import { resolveLocalTenantContext } from "@/lib/tenant-context";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const context = resolveLocalTenantContext();
  try {
    const body = await request.json();
    const client = createReferenceApiClient({ baseUrl: process.env.REFERENCE_API_URL ?? "http://localhost:8000", fetch: (input, init) => fetch(input, { ...init, headers: { ...init?.headers, "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId } }) });
    const result = await client.POST("/v1/market-data-resolution-snapshots", { body, params: { header: { "Idempotency-Key": crypto.randomUUID() } } });
    if (result.error || !result.data) return NextResponse.json({ error: result.error ?? { code: "MARKET_DATA_API_ERROR" } }, { status: result.response.status });
    return NextResponse.json(result.data, { status: result.response.status, headers: { Location: result.response.headers.get("location") ?? "" } });
  } catch (error) {
    return bffErrorResponse(error, "Market-data resolution service is unavailable.", request, "MARKET_DATA_RESOLUTION_API_UNAVAILABLE");
  }
}
