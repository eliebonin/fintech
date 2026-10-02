import { NextResponse } from "next/server";

import { decideReferenceDataProposal, getReferenceDataProposal } from "@/lib/reference-api-client";
import { bffErrorResponse } from "@/lib/bff-error";
import { getActiveTenantContext } from "@/lib/tenant-session";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await context.params;
  try {
    return NextResponse.json(await getReferenceDataProposal(proposalId, await getActiveTenantContext()));
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}

export async function POST(request: Request, context: { params: Promise<{ proposalId: string }> }) {
  const { proposalId } = await context.params;
  try {
    const payload = (await request.json()) as { decision: "APPROVED" | "REJECTED"; reason: string };
    const response = await decideReferenceDataProposal(proposalId, payload, await getActiveTenantContext());
    return NextResponse.json(response);
  } catch (error: unknown) {
    return bffErrorResponse(error, "Reference data service is unavailable", request);
  }
}
