import { NextResponse } from "next/server";

import { decideCryptoAssetProposal } from "@/lib/reference-api-client";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await context.params;
  try {
    const payload = (await request.json()) as { decision: "APPROVED" | "REJECTED"; reason: string };
    return NextResponse.json(await decideCryptoAssetProposal(proposalId, payload, resolveLocalTenantContext()));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
