import { NextResponse } from "next/server";

import { submitEquityListingProposal } from "@/lib/reference-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const context = await getActiveTenantContext();
    const payload = (await request.json()) as Record<string, unknown>;
    return NextResponse.json(await submitEquityListingProposal(payload, context), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
