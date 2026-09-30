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
    return NextResponse.json(await bookListedCashTrade(payload, context, idempotencyKey), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Trade booking service is unavailable", request, "TRADE_BOOKING_API_UNAVAILABLE");
  }
}
