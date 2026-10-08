import { NextResponse } from "next/server";

import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import { getWorkQueue } from "@/lib/work-queue";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const context = await requireReferenceTenantContext();
    return NextResponse.json(await getWorkQueue(context));
  } catch (error: unknown) {
    // A denied/unavailable queue must not masquerade as a successful demo queue.
    return bffErrorResponse(error, "Reference data service is unavailable", request, "REFERENCE_API_UNAVAILABLE");
  }
}
