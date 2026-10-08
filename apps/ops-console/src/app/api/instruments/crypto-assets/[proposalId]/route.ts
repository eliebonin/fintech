import { NextResponse } from "next/server";

import { getCryptoAssetProposal } from "@/lib/reference-api-client";
import { requireReferenceTenantContext } from "@/lib/reference-tenant-context";
import { bffErrorResponse } from "@/lib/bff-error";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await context.params;
  try {
    return NextResponse.json(await getCryptoAssetProposal(proposalId, await requireReferenceTenantContext()));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", _request);
  }
}
