import { NextResponse } from "next/server";

import { bffErrorResponse } from "@/lib/bff-error";
import { submitFxForwardProposal } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    return NextResponse.json(
      await submitFxForwardProposal((await request.json()) as Record<string, unknown>, await requireReferenceTenantContext()),
      { status: 201 },
    );
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
