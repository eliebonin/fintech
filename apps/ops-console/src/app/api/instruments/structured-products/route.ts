import { NextResponse } from "next/server";

import { submitStructuredProductProposal } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as Record<string, unknown>;
    return NextResponse.json(await submitStructuredProductProposal(payload, resolveLocalTenantContext()), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
