import { createReferenceApiClient } from "api-contracts";
import { NextRequest, NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import { resolveLocalTenantContext } from "@/lib/tenant-context";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const context = resolveLocalTenantContext();
  const valuationDate = request.nextUrl.searchParams.get("valuationDate");
  if (!valuationDate) return NextResponse.json({ error: { code: "VALUATION_DATE_REQUIRED" } }, { status: 400 });
  try {
    const client = createReferenceApiClient({ baseUrl: process.env.REFERENCE_API_URL ?? "http://localhost:8000", fetch: (input, init) => fetch(input, { ...init, headers: { ...init?.headers, "X-Tenant-Id": context.tenantId, "X-User-Account-Id": context.userAccountId } }) });
    const result = await client.GET("/v1/market-data/valuation-policies", { params: { query: { valuationDate } } });
    if (result.error || !result.data) return NextResponse.json({ error: result.error ?? { code: "MARKET_DATA_API_ERROR" } }, { status: result.response.status });
    return NextResponse.json(result.data);
  } catch (error) {
    return bffErrorResponse(error, "Market-data policy service is unavailable.", request, "MARKET_DATA_POLICY_API_UNAVAILABLE");
  }
}
