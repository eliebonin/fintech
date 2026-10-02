import { NextRequest, NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import { bookListedCashTrade, type TradeBookingRequest } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const idempotencyKey = request.headers.get("Idempotency-Key")?.trim();
  if (!idempotencyKey) {
    return NextResponse.json({ error: { code: "IDEMPOTENCY_KEY_REQUIRED", message: "Idempotency-Key is required." } }, { status: 400 });
  }

  let payload: TradeBookingRequest;
  try {
    payload = (await request.json()) as TradeBookingRequest;
  } catch {
    return bffErrorResponse(new Error("Request body must be valid JSON"), "Request body must be valid JSON", request, "INVALID_JSON");
  }

  let context;
  try {
    context = await getActiveTenantContext();
  } catch {
    return NextResponse.json({ error: { code: "ACTIVE_TENANT_REQUIRED" } }, { status: 401 });
  }

  try {
    const expectedTenant = request.headers.get("X-Expected-Tenant-Id");
    const enriched = ["properties", "tagIds", "traderPersonId", "executingBrokerOrganisationId", "tradePurpose", "marketActivity", "externalReferences"].some((field) => field in payload);
    if (expectedTenant && expectedTenant !== context.tenantId) return NextResponse.json({error:{code:"TENANT_CONTEXT_CHANGED", message:"The active tenant changed. Restart the ticket before booking."}}, {status:409});
    if (enriched && !expectedTenant) return NextResponse.json({error:{code:"EXPECTED_TENANT_REQUIRED",message:"Reopen the ticket to confirm its tenant context."}}, {status:400});
    return NextResponse.json(await bookListedCashTrade(payload, context, idempotencyKey), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Trade booking service is unavailable", request, "TRADE_BOOKING_API_UNAVAILABLE");
  }
}
