import { NextResponse } from "next/server";

import { submitIndexFamilyProposal } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const context = await requireReferenceTenantContext();
    const payload = (await request.json()) as Record<string, unknown>;
    return NextResponse.json(await submitIndexFamilyProposal(payload, context), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
