import { NextResponse } from "next/server";

import { submitIndexProposal } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as Record<string, unknown>;
    return NextResponse.json(await submitIndexProposal(payload, await requireReferenceTenantContext()), { status: 201 });
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
