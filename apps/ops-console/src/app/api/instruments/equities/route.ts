import { NextRequest, NextResponse } from "next/server";

import { submitEquityProposal } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    return bffErrorResponse(new Error("Request body must be valid JSON"), "Request body must be valid JSON", request, "INVALID_JSON");
  }
  try {
    const context = await requireReferenceTenantContext();
    return NextResponse.json(await submitEquityProposal(payload, context), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
